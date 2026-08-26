"""研究助手检索与报告执行器。

检索供应商通过接口抽象；Tavily 是当前实现候选，DeepSeek 联网能力或其他供应商
可在后续替换。所有凭证只从环境变量读取，不写入日志或数据库。
"""

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BizError, not_found
from app.models.base import utcnow
from app.models.phase2 import ResearchReference, ResearchReport, ResearchTask, ResearchTaskStatus
from app.services import deepseek_service


class SearchProviderError(Exception):
    """检索供应商调用失败，message 不包含凭证。"""

    def __init__(self, message: str, code: str = "SEARCH_FAILED"):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    content: str
    score: float | None
    raw: dict[str, Any]


class SearchProvider(Protocol):
    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        ...


class TavilySearchProvider:
    """Tavily Search API 实现；供应商选择仍属于待实测依赖。"""

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        if not settings.tavily_api_key:
            raise SearchProviderError(
                "TAVILY_API_KEY 未配置：请在 backend/.env 或运行环境中设置该环境变量",
                code="TAVILY_API_KEY_MISSING",
            )
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "max_results": max(1, min(max_results, 20)),
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        }
        try:
            with httpx.Client(timeout=settings.tavily_timeout) as client:
                response = client.post(settings.tavily_base_url, json=payload)
        except httpx.HTTPError as exc:
            raise SearchProviderError(f"Tavily 请求失败：{exc}", code="TAVILY_NETWORK_ERROR") from exc
        if response.status_code >= 400:
            raise SearchProviderError(
                f"Tavily 返回 HTTP {response.status_code}", code="TAVILY_HTTP_ERROR"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise SearchProviderError("Tavily 返回不是有效 JSON", code="TAVILY_INVALID_RESPONSE") from exc
        results = body.get("results") if isinstance(body, dict) else None
        if not isinstance(results, list):
            raise SearchProviderError("Tavily 返回缺少 results", code="TAVILY_INVALID_RESPONSE")
        hits: list[SearchHit] = []
        for item in results:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            hits.append(
                SearchHit(
                    title=str(item.get("title") or item["url"]),
                    url=str(item["url"]),
                    content=str(item.get("content") or ""),
                    score=_float_or_none(item.get("score")),
                    raw=item,
                )
            )
        return hits


def get_search_provider(task: ResearchTask) -> SearchProvider:
    """返回当前检索供应商；后续可替换为 DeepSeek 官方搜索等实现。"""

    provider = (task.scope_config or {}).get("search_provider", "tavily")
    if provider != "tavily":
        raise SearchProviderError(
            f"检索供应商「{provider}」尚未实测或实现；DeepSeek 官方搜索可后续接入",
            code="SEARCH_PROVIDER_NOT_AVAILABLE",
        )
    return TavilySearchProvider()


def execute_task(db: Session, task_id: int) -> ResearchTask:
    """同步执行研究任务：检索 -> 整理 -> 报告 -> 引用。"""

    task = db.get(ResearchTask, task_id)
    if task is None:
        raise not_found("研究任务")
    if task.status not in {ResearchTaskStatus.pending, ResearchTaskStatus.failed}:
        raise BizError(
            f"当前状态「{task.status.value}」不可执行（仅 pending/failed 可执行）",
            code=409,
        )

    task.status = ResearchTaskStatus.searching
    task.current_stage = "searching"
    task.progress_percent = 0
    task.progress_message = "正在检索来源"
    task.last_error_code = None
    task.last_error_message = None
    task.started_at = utcnow()
    task.finished_at = None
    db.commit()

    try:
        hits = _search(task)
    except SearchProviderError as exc:
        _mark_failed(db, task, exc.code, exc.message)
        raise BizError(f"研究任务检索失败：{exc.message}") from exc

    task.status = ResearchTaskStatus.organizing
    task.current_stage = "organizing"
    task.progress_percent = 60
    task.progress_message = f"已获得 {len(hits)} 条可引用来源，正在整理报告"
    task.checkpoint_data = {
        "search_provider": "tavily",
        "source_count": len(hits),
        "source_urls": [hit.url for hit in hits],
        "saved_at": utcnow().isoformat(),
    }
    db.commit()

    try:
        report_payload, raw_response = _generate_report(task, hits)
        archive_path = deepseek_service.archive_raw(raw_response, "research")
        report = _upsert_report(db, task, report_payload, raw_response, archive_path, len(hits))
        for hit in hits:
            db.add(
                ResearchReference(
                    report_id=report.id,
                    source_kind="external_url",
                    source_url=hit.url,
                    source_title=hit.title,
                    search_provider="tavily",
                    source_snapshot=json.dumps(hit.raw, ensure_ascii=False),
                    evidence_summary=hit.content or None,
                    source_type="web_search",
                    cited_at=utcnow(),
                )
            )
        task.status = ResearchTaskStatus.success
        task.current_stage = "completed"
        task.progress_percent = 100
        task.progress_message = "研究报告已生成"
        task.finished_at = utcnow()
        task.last_error_code = None
        task.last_error_message = None
        db.commit()
        db.refresh(task)
        return task
    except deepseek_service.DeepSeekError as exc:
        archive_path = deepseek_service.archive_raw(exc.raw, "research_failed") if exc.raw else None
        detail = exc.message
        if archive_path:
            detail = f"{detail}；原始响应留档：{archive_path}"
        _mark_failed(db, task, "DEEPSEEK_FAILED", detail)
        raise BizError(f"研究报告整理失败，可重试。原因：{detail}") from exc
    except BizError as exc:
        _mark_failed(db, task, "DEEPSEEK_CONFIG_ERROR", str(exc.detail))
        raise
    except Exception as exc:  # noqa: BLE001 - 记录失败状态后交给 API 层
        _mark_failed(db, task, "REPORT_GENERATION_FAILED", f"报告生成失败：{exc}")
        raise BizError("研究报告生成失败，可重试") from exc


def retry_task(db: Session, task_id: int) -> ResearchTask:
    task = db.get(ResearchTask, task_id)
    if task is None:
        raise not_found("研究任务")
    if task.status != ResearchTaskStatus.failed:
        raise BizError("只有 failed 状态的研究任务可重试", code=409)
    task.retry_count += 1
    db.commit()
    return execute_task(db, task_id)


def _search(task: ResearchTask) -> list[SearchHit]:
    config = task.scope_config or {}
    query = str(config.get("query") or f"{task.topic}\n研究目标：{task.objective}")
    max_results = _int_or_default(config.get("max_results"), 5)
    return get_search_provider(task).search(query, max_results=max_results)


def _generate_report(task: ResearchTask, hits: list[SearchHit]) -> tuple[dict[str, Any], str]:
    source_block = "\n".join(
        f"[{index}] 标题：{hit.title}\nURL：{hit.url}\n摘要：{hit.content}"
        for index, hit in enumerate(hits, start=1)
    )
    if not source_block:
        source_block = "（本次检索没有返回可引用来源；报告必须明确标注引用缺失，不得把推断写成已核验事实。）"
    system_prompt = (
        "你是 Forge 研究助手。请只输出 JSON 对象，字段必须包含 title、summary、content、sections、conclusions。"
        "来源先于结论：只能把给定来源作为事实依据，无法由来源支持的内容必须标注为推断或引用缺失。"
        "sections 和 conclusions 必须是 JSON 对象，内容中用 [1] 这样的编号指向来源。"
    )
    user_prompt = (
        f"研究主题：{task.topic}\n研究目标：{task.objective}\n\n可用检索来源：\n{source_block}\n\n"
        "请生成中文研究报告。若没有来源，summary、content 和 conclusions 都必须明确说明“引用缺失/未找到可用来源”。"
    )
    return deepseek_service.chat_json(
        system_prompt,
        user_prompt,
        validator=_validate_report_payload,
        temperature=0.4,
    )


def _validate_report_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("研究报告输出必须是 JSON 对象")
    required = ("title", "summary", "content", "sections", "conclusions")
    if any(not str(payload.get(key) or "").strip() for key in required[:3]):
        raise ValueError("研究报告缺少 title/summary/content")
    if not isinstance(payload.get("sections"), dict) or not isinstance(payload.get("conclusions"), dict):
        raise ValueError("研究报告 sections/conclusions 必须是 JSON 对象")
    return payload


def _upsert_report(
    db: Session,
    task: ResearchTask,
    payload: dict[str, Any],
    raw_response: str,
    archive_path: str,
    source_count: int,
) -> ResearchReport:
    report = db.scalar(select(ResearchReport).where(ResearchReport.research_task_id == task.id))
    if report is None:
        report = ResearchReport(research_task_id=task.id)
        db.add(report)
    report.title = str(payload["title"])
    report.summary = str(payload["summary"])
    report.content = str(payload["content"])
    report.sections = payload["sections"]
    report.conclusions = payload["conclusions"]
    report.generation_trace = {
        "task_id": task.id,
        "source_count": source_count,
        "raw_response_archive": archive_path,
        "generated_at": utcnow().isoformat(),
    }
    report.raw_ai_response = raw_response
    report.is_ai_product = True
    report.source_count = source_count
    db.flush()
    return report


def _mark_failed(db: Session, task: ResearchTask, code: str, message: str) -> None:
    task.status = ResearchTaskStatus.failed
    task.current_stage = "failed"
    task.progress_message = message
    task.last_error_code = code
    task.last_error_message = message
    task.finished_at = utcnow()
    task.retry_count = task.retry_count or 0
    db.commit()


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _int_or_default(value: Any, default: int) -> int:
    try:
        return max(1, min(int(value), 20)) if value is not None else default
    except (TypeError, ValueError):
        return default
