"""数据分析服务（模块 04）。

D-T1：分析任务一期同步执行（点击执行 → 等待 → 出结果），不做异步队列/轮询/通知。
S03：失败保留错误原因与 AI 原始响应，可重试（DeepSeek 封装内部已重试 3 次指数退避）。
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MaterialStatus
from app.core.exceptions import BizError
from app.models.analysis import (
    AnalysisResult,
    AnalysisResultMaterial,
    AnalysisResultTopic,
    AnalysisTask,
    AnalysisTaskInput,
    RawData,
)
from app.models.material import Material
from app.models.prompt import PromptTemplate
from app.schemas.analysis import AnalysisResultOut, AnalysisTaskOut, RawDataOut

# 结构化输出的内置字段定义（context/05 §4.7：结果含「效果好坏 / 结论 / 建议」）
DEFAULT_OUTPUT_SCHEMA: dict = {
    "results": [
        {
            "effect": "效果好坏的判断，字符串",
            "conclusion": "分析结论，字符串",
            "suggestions": ["可执行建议，字符串数组"],
            "evidence": "支撑依据，字符串（可选）",
            "material_candidates": [
                {"title": "可回写资料库的标题", "content": "资料正文"}
            ],
            "topic_candidates": [{"title": "可反哺的选题标题", "core_angle": "内容核心角度"}],
        }
    ]
}

DEFAULT_SYSTEM_PROMPT = (
    "你是资深新媒体数据分析师，服务对象是面向中小微企业主的企业线上营销与获客账号。"
    "请严格输出 JSON 对象，不要输出任何解释文字。"
)

DEFAULT_USER_PROMPT_TEMPLATE = """请对以下{task_type}输入数据做结构化分析。

{material_block}

待分析数据：
{data_block}

输出 JSON 格式（严格遵守）：
{{
  "results": [
    {{
      "effect": "效果好坏的判断",
      "conclusion": "分析结论",
      "suggestions": ["建议1", "建议2"],
      "evidence": "支撑依据",
      "material_candidates": [{{"title": "可沉淀为资料的标题", "content": "资料正文"}}],
      "topic_candidates": [{{"title": "可反哺的选题标题", "core_angle": "内容核心角度"}}]
    }}
  ]
}}

要求：
1. conclusion 必须非空，且基于给定数据，不得编造数字；
2. suggestions 至少 1 条；
3. material_candidates / topic_candidates 可以为空数组；
4. 只输出 JSON。"""


def validate_analysis_payload(data: Any) -> list[dict]:
    """校验 AI 结构化输出（S03：不符合结构即判失败并重试）。"""
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("results")
    else:
        raise ValueError("AI 输出不是 JSON 对象或数组")
    if not isinstance(items, list) or not items:
        raise ValueError("AI 输出缺少非空的 results 数组")

    cleaned: list[dict] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {idx} 条结果不是对象")
        conclusion = item.get("conclusion")
        if not isinstance(conclusion, str) or not conclusion.strip():
            raise ValueError(f"第 {idx} 条结果缺少 conclusion")
        suggestions = item.get("suggestions") or []
        if isinstance(suggestions, str):
            suggestions = [suggestions]
        if not isinstance(suggestions, list) or not suggestions:
            raise ValueError(f"第 {idx} 条结果缺少 suggestions")
        cleaned.append(
            {
                "effect": str(item.get("effect") or "").strip(),
                "conclusion": conclusion.strip(),
                "suggestions": [str(s).strip() for s in suggestions if str(s).strip()],
                "evidence": str(item.get("evidence") or "").strip(),
                "material_candidates": _clean_candidates(
                    item.get("material_candidates"), ("title", "content")
                ),
                "topic_candidates": _clean_candidates(
                    item.get("topic_candidates"), ("title", "core_angle")
                ),
            }
        )
    return cleaned


def _clean_candidates(value: Any, fields: tuple[str, ...]) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        row = {f: str(item.get(f) or "").strip() for f in fields}
        if row.get(fields[0]):
            out.append(row)
    return out


def build_material_snapshot(db: Session, material_ids: list[int]) -> tuple[str, dict | None]:
    """资料库上下文快照；仅允许引用「已生效」资料（R1）。"""
    if not material_ids:
        return "本次不提供资料库上下文。", None
    rows = list(db.scalars(select(Material).where(Material.id.in_(material_ids))).all())
    missing = set(material_ids) - {r.id for r in rows}
    if missing:
        raise BizError(f"资料不存在：{sorted(missing)}")
    invalid = [r.title for r in rows if r.status != MaterialStatus.已生效]
    if invalid:
        raise BizError(f"资料必须为「已生效」状态（R1）：{'、'.join(invalid)}")
    block = "资料库上下文：\n" + "\n".join(f"- {r.title}：{r.content[:500]}" for r in rows)
    snapshot = {
        "material_ids": [r.id for r in rows],
        "items": [{"id": r.id, "title": r.title, "content": r.content[:2000]} for r in rows],
    }
    return block, snapshot


def build_data_block(rows: list[RawData]) -> str:
    lines: list[str] = []
    for r in rows:
        source = r.data_source.name if r.data_source else f"数据源{r.source_id}"
        window = f"{r.window_start:%Y-%m-%d} ~ {r.window_end:%Y-%m-%d}"
        lines.append(f"【{source}｜{window}】{(r.raw_content or '')[:2000]}")
        if r.structured:
            lines.append(f"  结构化字段：{r.structured}")
    return "\n".join(lines) if lines else "（无内容）"


def build_prompt(
    db: Session,
    task_type: str,
    rows: list[RawData],
    material_ids: list[int],
    template_id: int | None,
) -> tuple[str, str, dict | None, dict | None, dict]:
    """返回 (system_prompt, user_prompt, prompt_snapshot, material_snapshot, output_schema)。"""
    material_block, material_snapshot = build_material_snapshot(db, material_ids)
    system_prompt = DEFAULT_SYSTEM_PROMPT
    output_schema = DEFAULT_OUTPUT_SCHEMA
    # 未选模板时也留快照（内置模板），保证 S04 追溯完整
    prompt_snapshot: dict | None = {
        "template_id": None,
        "name": "内置分析提示词",
        "version": 0,
        "content_snapshot": DEFAULT_SYSTEM_PROMPT,
    }

    if template_id is not None:
        template = db.get(PromptTemplate, template_id)
        if template is None:
            raise BizError("提示词模板不存在")
        system_prompt = template.content
        output_schema = template.output_schema or DEFAULT_OUTPUT_SCHEMA
        prompt_snapshot = {
            "template_id": template.id,
            "name": template.name,
            "version": template.version,
            "content_snapshot": template.content,
        }

    user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(
        task_type=task_type,
        material_block=material_block,
        data_block=build_data_block(rows),
    )
    return system_prompt, user_prompt, prompt_snapshot, material_snapshot, output_schema


def result_to_out(db: Session, result: AnalysisResult) -> AnalysisResultOut:
    out = AnalysisResultOut.model_validate(result)
    out.material_ids = [
        row.material_id
        for row in db.scalars(
            select(AnalysisResultMaterial).where(AnalysisResultMaterial.result_id == result.id)
        ).all()
    ]
    out.topic_ids = [
        row.topic_id
        for row in db.scalars(
            select(AnalysisResultTopic).where(AnalysisResultTopic.result_id == result.id)
        ).all()
    ]
    return out


def task_to_out(db: Session, task: AnalysisTask) -> AnalysisTaskOut:
    out = AnalysisTaskOut.model_validate(task)
    out.has_ai_raw_response = bool(task.ai_raw_response)
    out.raw_data_ids = [
        row.raw_data_id
        for row in db.scalars(
            select(AnalysisTaskInput).where(AnalysisTaskInput.task_id == task.id)
        ).all()
    ]
    out.results = [
        result_to_out(db, r)
        for r in db.scalars(
            select(AnalysisResult).where(AnalysisResult.task_id == task.id).order_by(AnalysisResult.id)
        ).all()
    ]
    return out


def raw_to_out(raw: RawData) -> RawDataOut:
    out = RawDataOut.model_validate(raw)
    out.source_name = raw.data_source.name if raw.data_source else None
    return out
