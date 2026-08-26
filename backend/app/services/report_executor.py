"""数据报告生成执行器。

运营数据报告：聚合已确认分析任务结果 + 周期内采集结果 + 业务原始数据。
市场分析周报：聚合研究助手报告 + 采集结果 + 外部检索引用。
数据源为空时明确失败，不伪造指标或结论。同步执行；失败可重试并保留历史错误。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisTaskStatus
from app.core.exceptions import BizError, not_found
from app.models.analysis import AnalysisResult, AnalysisTask, RawData
from app.models.base import utcnow
from app.models.phase2 import (
    CollectionResult,
    ResearchReference,
    ResearchReport,
    ResearchReportStatus,
)
from app.models.report import Report, ReportGenerationStatus, ReportReviewStatus, ReportType

EMPTY_SOURCE_CODE = "EMPTY_SOURCE"
IN_PROGRESS_CODE = 409


def generate_report(db: Session, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise not_found("报告")
    if report.generation_status == ReportGenerationStatus.生成中:
        raise BizError("报告正在生成中，禁止重复触发", code=IN_PROGRESS_CODE)
    if report.generation_status == ReportGenerationStatus.已完成:
        raise BizError("已完成报告不可再次生成，失败报告请使用重试", code=IN_PROGRESS_CODE)
    if report.generation_status not in {ReportGenerationStatus.待生成, ReportGenerationStatus.失败}:
        raise BizError(f"当前状态「{report.generation_status.value}」不可生成", code=IN_PROGRESS_CODE)

    report.generation_status = ReportGenerationStatus.生成中
    db.commit()

    try:
        sources, gaps = _collect_sources(db, report)
        if not sources:
            raise SourceEmptyError(_empty_message(report.report_type), gaps)

        payload = _build_payload(report, sources, gaps)
        snapshot = {
            "sources": [
                {"type": item["type"], "id": item["id"], **item.get("meta", {})} for item in sources
            ],
            "gaps": gaps,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
        }
        previous_errors = _error_history(report)
        report.title = payload["title"]
        report.summary = payload["summary"]
        report.content = payload["content"]
        report.sections = payload["sections"]
        report.conclusions = payload["conclusions"]
        report.source_snapshot = snapshot
        report.generation_trace = {
            "generated_at": utcnow().isoformat(),
            "source_count": len(sources),
            "gaps": gaps,
            "error_history": previous_errors,
            "mode": "aggregate",
        }
        report.is_ai_product = True
        report.generation_status = ReportGenerationStatus.已完成
        report.review_status = ReportReviewStatus.默认通过
        report.error_code = None
        report.error_message = None
        report.generated_at = utcnow()
        db.commit()
        db.refresh(report)
        return report
    except SourceEmptyError as exc:
        _mark_failed(db, report, EMPTY_SOURCE_CODE, exc.message, exc.gaps)
        raise BizError(exc.message) from exc
    except BizError:
        raise
    except Exception as exc:  # noqa: BLE001
        _mark_failed(db, report, "REPORT_GENERATION_FAILED", f"报告生成失败：{exc}", [])
        raise BizError("报告生成失败，可重试") from exc


def retry_report(db: Session, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise not_found("报告")
    if report.generation_status != ReportGenerationStatus.失败:
        raise BizError("只有失败状态的报告可重试", code=IN_PROGRESS_CODE)
    history = _error_history(report)
    if report.error_code or report.error_message:
        history.append(
            {
                "error_code": report.error_code,
                "error_message": report.error_message,
                "retried_at": utcnow().isoformat(),
            }
        )
    trace = dict(report.generation_trace or {})
    trace["error_history"] = history
    report.generation_trace = trace
    report.retry_count = (report.retry_count or 0) + 1
    report.generation_status = ReportGenerationStatus.待生成
    db.commit()
    return generate_report(db, report_id)


class SourceEmptyError(Exception):
    def __init__(self, message: str, gaps: list[str]):
        super().__init__(message)
        self.message = message
        self.gaps = gaps


def _collect_sources(db: Session, report: Report) -> tuple[list[dict[str, Any]], list[str]]:
    if report.report_type == ReportType.运营数据报告:
        return _collect_ops_sources(db, report)
    return _collect_market_sources(db, report)


def _collect_ops_sources(db: Session, report: Report) -> tuple[list[dict[str, Any]], list[str]]:
    config = report.source_config or {}
    sources: list[dict[str, Any]] = []
    gaps: list[str] = []

    analysis_rows = _load_analysis(db, report, config)
    for task, result in analysis_rows:
        sources.append(
            {
                "type": "analysis_task",
                "id": task.id,
                "meta": {"name": task.name, "status": task.status.value, "result_id": result.id},
                "payload": result.result_content or {},
            }
        )
    if not analysis_rows:
        gaps.append("周期内无已确认分析任务结果")

    collection_rows = _load_collection_results(db, report, config)
    for row in collection_rows:
        sources.append(
            {
                "type": "collection_result",
                "id": row.id,
                "meta": {
                    "platform": row.platform,
                    "account_identifier": row.account_identifier,
                    "task_id": row.task_id,
                },
                "payload": {
                    "raw_content": _clip(row.raw_content),
                    "structured_data": row.structured_data,
                    "source_url": row.source_url,
                },
            }
        )
    if not collection_rows:
        gaps.append("周期内无可用采集结果")

    raw_rows = _load_raw_data(db, report, config)
    for row in raw_rows:
        sources.append(
            {
                "type": "raw_data",
                "id": row.id,
                "meta": {"source_id": row.source_id},
                "payload": {
                    "raw_content": _clip(row.raw_content),
                    "structured": row.structured,
                },
            }
        )
    if not raw_rows:
        gaps.append("周期内无业务原始数据")

    return sources, gaps


def _collect_market_sources(db: Session, report: Report) -> tuple[list[dict[str, Any]], list[str]]:
    config = report.source_config or {}
    sources: list[dict[str, Any]] = []
    gaps: list[str] = []

    research_rows = _load_research_reports(db, report, config)
    for row in research_rows:
        sources.append(
            {
                "type": "research_report",
                "id": row.id,
                "meta": {"title": row.title, "research_task_id": row.research_task_id},
                "payload": {
                    "summary": row.summary,
                    "content": _clip(row.content),
                    "conclusions": row.conclusions,
                },
            }
        )
    if not research_rows:
        gaps.append("周期内无研究助手报告")

    collection_rows = _load_collection_results(db, report, config)
    for row in collection_rows:
        sources.append(
            {
                "type": "collection_result",
                "id": row.id,
                "meta": {
                    "platform": row.platform,
                    "account_identifier": row.account_identifier,
                    "task_id": row.task_id,
                },
                "payload": {
                    "raw_content": _clip(row.raw_content),
                    "structured_data": row.structured_data,
                    "source_url": row.source_url,
                },
            }
        )
    if not collection_rows:
        gaps.append("周期内无可用采集结果")

    references = _load_external_references(db, report, config)
    for row in references:
        sources.append(
            {
                "type": "research_reference",
                "id": row.id,
                "meta": {
                    "source_kind": row.source_kind,
                    "source_url": row.source_url,
                    "source_title": row.source_title,
                },
                "payload": {
                    "evidence_summary": row.evidence_summary,
                    "source_snapshot": _clip(row.source_snapshot),
                },
            }
        )
    if not references:
        gaps.append("周期内无外部检索结论/引用")

    return sources, gaps


def _load_analysis(db: Session, report: Report, config: dict[str, Any]) -> list[tuple[AnalysisTask, AnalysisResult]]:
    ids = _id_list(config.get("analysis_task_ids"))
    stmt = (
        select(AnalysisTask, AnalysisResult)
        .join(AnalysisResult, AnalysisResult.task_id == AnalysisTask.id)
        .where(AnalysisTask.status == AnalysisTaskStatus.已确认)
        .where(AnalysisTask.created_at >= report.period_start)
        .where(AnalysisTask.created_at <= report.period_end)
    )
    if ids:
        stmt = stmt.where(AnalysisTask.id.in_(ids))
    return list(db.execute(stmt.order_by(AnalysisTask.id.desc())).all())


def _load_collection_results(db: Session, report: Report, config: dict[str, Any]) -> list[CollectionResult]:
    ids = _id_list(config.get("collection_result_ids"))
    stmt = select(CollectionResult).where(
        CollectionResult.collected_at >= report.period_start,
        CollectionResult.collected_at <= report.period_end,
    )
    if ids:
        stmt = stmt.where(CollectionResult.id.in_(ids))
    return list(db.scalars(stmt.order_by(CollectionResult.id.desc())).all())


def _load_raw_data(db: Session, report: Report, config: dict[str, Any]) -> list[RawData]:
    ids = _id_list(config.get("raw_data_ids"))
    stmt = select(RawData).where(
        or_(
            RawData.collected_at.between(report.period_start, report.period_end),
            RawData.window_start.between(report.period_start, report.period_end),
        )
    )
    if ids:
        stmt = stmt.where(RawData.id.in_(ids))
    return list(db.scalars(stmt.order_by(RawData.id.desc())).all())


def _load_research_reports(db: Session, report: Report, config: dict[str, Any]) -> list[ResearchReport]:
    ids = _id_list(config.get("research_report_ids"))
    stmt = select(ResearchReport).where(
        ResearchReport.status == ResearchReportStatus.success,
        ResearchReport.created_at >= report.period_start,
        ResearchReport.created_at <= report.period_end,
    )
    if ids:
        stmt = stmt.where(ResearchReport.id.in_(ids))
    return list(db.scalars(stmt.order_by(ResearchReport.id.desc())).all())


def _load_external_references(db: Session, report: Report, config: dict[str, Any]) -> list[ResearchReference]:
    ids = _id_list(config.get("research_reference_ids"))
    stmt = select(ResearchReference).where(
        ResearchReference.source_kind == "external_url",
        ResearchReference.cited_at >= report.period_start,
        ResearchReference.cited_at <= report.period_end,
    )
    if ids:
        stmt = stmt.where(ResearchReference.id.in_(ids))
    return list(db.scalars(stmt.order_by(ResearchReference.id.desc())).all())


def _build_payload(report: Report, sources: list[dict[str, Any]], gaps: list[str]) -> dict[str, Any]:
    period_label = f"{_fmt(report.period_start)} 至 {_fmt(report.period_end)}"
    title = report.title.strip() or f"{report.report_type.value}（{period_label}）"
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in sources:
        grouped.setdefault(item["type"], []).append(item)

    gap_text = "；".join(gaps) if gaps else "本期主要来源齐全"
    source_lines = [
        f"- [{item['type']}#{item['id']}] {item.get('meta') or {}}"
        for item in sources
    ]
    body_parts = [
        f"报告类型：{report.report_type.value}",
        f"统计周期：{period_label}",
        f"来源数量：{len(sources)}",
        f"来源缺口：{gap_text}",
        "来源清单（先于结论）：",
        *source_lines,
        "",
        "来源摘要：",
    ]
    for item in sources:
        body_parts.append(_source_excerpt(item))

    if report.report_type == ReportType.运营数据报告:
        conclusions = _ops_conclusions(grouped, gaps)
        sections = {
            "分析任务结果": [_brief(item) for item in grouped.get("analysis_task", [])],
            "采集结果": [_brief(item) for item in grouped.get("collection_result", [])],
            "业务原始数据": [_brief(item) for item in grouped.get("raw_data", [])],
            "来源缺口": gaps,
        }
        summary = (
            f"本周运营数据报告共引用 {len(sources)} 条来源。"
            f"其中分析任务 {len(grouped.get('analysis_task', []))} 条、"
            f"采集结果 {len(grouped.get('collection_result', []))} 条、"
            f"业务数据 {len(grouped.get('raw_data', []))} 条。"
            f"缺口：{gap_text}。结论仅基于上述来源，未补造缺失指标。"
        )
    else:
        conclusions = _market_conclusions(grouped, gaps)
        sections = {
            "研究助手报告": [_brief(item) for item in grouped.get("research_report", [])],
            "采集结果": [_brief(item) for item in grouped.get("collection_result", [])],
            "外部检索结论": [_brief(item) for item in grouped.get("research_reference", [])],
            "来源缺口": gaps,
        }
        summary = (
            f"本周市场分析周报共引用 {len(sources)} 条来源。"
            f"其中研究报告 {len(grouped.get('research_report', []))} 条、"
            f"采集结果 {len(grouped.get('collection_result', []))} 条、"
            f"外部检索 {len(grouped.get('research_reference', []))} 条。"
            f"缺口：{gap_text}。趋势/竞对判断仅在有引用时给出，缺失处已标注。"
        )

    return {
        "title": title[:500],
        "summary": summary,
        "content": "\n".join(body_parts),
        "sections": sections,
        "conclusions": conclusions,
    }


def _ops_conclusions(grouped: dict[str, list[dict[str, Any]]], gaps: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in grouped.get("analysis_task", []):
        payload = item.get("payload") or {}
        items.append(
            {
                "source": f"analysis_task#{item['id']}",
                "conclusion": payload.get("conclusion") or payload.get("effect") or "见来源结构化结果",
                "suggestions": payload.get("suggestions") or [],
            }
        )
    if not items:
        items.append({"source": None, "conclusion": "无已确认分析结论，不推断运营效果", "suggestions": []})
    return {"items": items, "gaps": gaps, "note": "来源先于结论；缺口未用模型猜测填补"}


def _market_conclusions(grouped: dict[str, list[dict[str, Any]]], gaps: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in grouped.get("research_report", []):
        payload = item.get("payload") or {}
        items.append(
            {
                "source": f"research_report#{item['id']}",
                "conclusion": payload.get("summary") or "见研究报告正文",
            }
        )
    for item in grouped.get("research_reference", []):
        meta = item.get("meta") or {}
        payload = item.get("payload") or {}
        items.append(
            {
                "source": f"research_reference#{item['id']}",
                "conclusion": payload.get("evidence_summary") or meta.get("source_title") or "外部检索条目",
                "url": meta.get("source_url"),
            }
        )
    if not items:
        items.append({"source": None, "conclusion": "引用缺失/未找到可用来源，不把推断写成已核验事实"})
    return {"items": items, "gaps": gaps, "note": "来源先于结论；无引用处已标注缺失"}


def _brief(item: dict[str, Any]) -> dict[str, Any]:
    return {"id": item["id"], "type": item["type"], "meta": item.get("meta") or {}}


def _source_excerpt(item: dict[str, Any]) -> str:
    payload = item.get("payload") or {}
    text = payload.get("summary") or payload.get("conclusion") or payload.get("raw_content") or payload.get("evidence_summary")
    if not text and isinstance(payload.get("structured"), dict):
        text = str(payload.get("structured"))
    return f"[{item['type']}#{item['id']}] {_clip(str(text or '（来源无摘要）'), 400)}"


def _empty_message(report_type: ReportType) -> str:
    if report_type == ReportType.运营数据报告:
        return "运营数据报告生成失败：周期内无分析任务结果、采集结果或业务原始数据，拒绝伪造数据"
    return "市场分析周报生成失败：周期内无研究助手报告、采集结果或外部检索结论，拒绝伪造数据"


def _mark_failed(db: Session, report: Report, code: str, message: str, gaps: list[str]) -> None:
    previous = _error_history(report)
    report.generation_status = ReportGenerationStatus.失败
    report.error_code = code
    report.error_message = message
    snapshot = dict(report.source_snapshot or {})
    snapshot["gaps"] = gaps or snapshot.get("gaps") or [message]
    snapshot["sources"] = snapshot.get("sources") or []
    report.source_snapshot = snapshot
    trace = dict(report.generation_trace or {})
    trace["error_history"] = previous
    trace["last_failed_at"] = utcnow().isoformat()
    report.generation_trace = trace
    report.generated_at = None
    db.commit()


def _error_history(report: Report) -> list[dict[str, Any]]:
    trace = report.generation_trace or {}
    history = trace.get("error_history") if isinstance(trace, dict) else None
    if isinstance(history, list):
        return list(history)
    return []


def _id_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    ids: list[int] = []
    for item in value:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def _clip(value: str | None, limit: int = 800) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _fmt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")
