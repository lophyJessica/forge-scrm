"""选题服务：批量生成（DeepSeek）、完全重复去重、输出装配。

R4/R14：每方向 10 条、保留历史批次、一期只做完全重复去重（同批次内 + 跨批次），语义去重二期。
"""

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MaterialStatus, Specialty
from app.core.exceptions import BizError
from app.models.material import Material
from app.models.prompt import PromptTemplate
from app.models.topic import Topic, TopicMaterial
from app.schemas.topic import TopicOut

# AI 输出必须包含的字段（对齐 context/05 §4.4 选题维度）
TOPIC_FIELDS = [
    "title",
    "customer_scenario",
    "user_perspective",
    "business_direction",
    "core_angle",
    "topic_principle",
    "topic_angle",
]

_FIELD_MAXLEN = {
    "title": 200,
    "customer_scenario": 200,
    "user_perspective": 200,
    "business_direction": 100,
    "core_angle": 500,
    "topic_principle": 200,
    "topic_angle": 200,
}

DEFAULT_SYSTEM_PROMPT = (
    "你是资深新媒体内容策划，服务对象是面向中小微企业主的企业线上营销与获客账号。"
    "请严格输出 JSON 对象，不要输出任何解释文字。"
)

DEFAULT_USER_PROMPT_TEMPLATE = """请围绕业务方向「{direction}」、专业方向「{specialty}」生成 {count} 条选题。

{material_block}

输出 JSON 格式（严格遵守，topics 数组长度为 {count}）：
{{
  "topics": [
    {{
      "title": "选题标题",
      "customer_scenario": "结合的客户需求场景",
      "user_perspective": "面向的用户视角",
      "business_direction": "叠加的经营方向",
      "core_angle": "内容核心角度",
      "topic_principle": "选题原则",
      "topic_angle": "选题角度"
    }}
  ]
}}

要求：
1. {count} 条选题彼此不得重复，标题不得雷同；
2. 每个字段都必须是非空中文字符串；
3. 只输出 JSON，不要 markdown 代码块以外的任何文字。"""


def normalize_title(title: str) -> str:
    """归一化标题用于「完全重复」判定：去空白、去常见标点、转小写。"""
    text = re.sub(r"\s+", "", title or "")
    text = re.sub(r"[，。！？、；：“”‘’\"'（）()《》【】\[\]—\-~·.,!?;:]", "", text)
    return text.lower()


def validate_topics_payload(count: int):
    """构造 DeepSeek 输出校验器（结构/非空/长度）。"""

    def _validate(data: Any) -> list[dict]:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("topics")
        else:
            raise ValueError("AI 输出不是 JSON 对象或数组")
        if not isinstance(items, list) or not items:
            raise ValueError("AI 输出缺少非空的 topics 数组")

        cleaned: list[dict] = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"第 {idx} 条选题不是对象")
            row = {}
            for field in TOPIC_FIELDS:
                value = item.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"第 {idx} 条选题字段 {field} 缺失或为空")
                row[field] = value.strip()[: _FIELD_MAXLEN[field]]
            cleaned.append(row)
        return cleaned

    return _validate


def build_material_block(db: Session, material_ids: list[int]) -> tuple[str, list[Material]]:
    """组装参考资料上下文；仅允许引用「已生效」资料（R1：审核后才能使用）。"""
    if not material_ids:
        return "本次不提供参考资料，请基于通用商业常识生成。", []
    rows = list(db.scalars(select(Material).where(Material.id.in_(material_ids))).all())
    missing = set(material_ids) - {r.id for r in rows}
    if missing:
        raise BizError(f"参考资料不存在：{sorted(missing)}")
    invalid = [r.title for r in rows if r.status != MaterialStatus.已生效]
    if invalid:
        raise BizError(f"参考资料必须为「已生效」状态（R1），以下资料不可引用：{'、'.join(invalid)}")
    lines = ["参考资料（请结合以下事实，不要编造数据）："]
    for r in rows:
        lines.append(f"- 【{r.material_class.name if r.material_class else ''}】{r.title}：{r.content[:500]}")
    return "\n".join(lines), rows


def build_prompt(
    db: Session,
    direction: str,
    specialty: Specialty,
    count: int,
    material_ids: list[int],
    template_id: int | None,
) -> tuple[str, str, dict | None, list[Material]]:
    material_block, materials = build_material_block(db, material_ids)
    system_prompt = DEFAULT_SYSTEM_PROMPT
    # 未选模板时也留快照（内置模板），保证 S04 追溯完整
    snapshot: dict | None = {
        "template_id": None,
        "name": "内置选题生成提示词",
        "version": 0,
        "content_snapshot": DEFAULT_SYSTEM_PROMPT,
    }

    if template_id is not None:
        template = db.get(PromptTemplate, template_id)
        if template is None:
            raise BizError("提示词模板不存在")
        system_prompt = template.content
        snapshot = {
            "template_id": template.id,
            "name": template.name,
            "version": template.version,
            "content_snapshot": template.content,
        }

    user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(
        direction=direction,
        specialty=specialty.value,
        count=count,
        material_block=material_block,
    )
    return system_prompt, user_prompt, snapshot, materials


def new_batch_no() -> str:
    return f"B{uuid.uuid4().hex[:12].upper()}"


def existing_title_keys(db: Session) -> set[str]:
    """跨批次已有选题标题（归一化）集合。"""
    return {normalize_title(t) for t in db.scalars(select(Topic.title)).all()}


def to_out(db: Session, topic: Topic) -> TopicOut:
    out = TopicOut.model_validate(topic)
    out.has_ai_raw_response = bool(topic.ai_raw_response)
    out.material_ids = [
        row.material_id
        for row in db.scalars(
            select(TopicMaterial).where(TopicMaterial.topic_id == topic.id)
        ).all()
    ]
    return out


def set_topic_materials(db: Session, topic: Topic, material_ids: list[int]) -> None:
    db.query(TopicMaterial).filter(TopicMaterial.topic_id == topic.id).delete()
    db.flush()
    for mid in dict.fromkeys(material_ids):
        db.add(TopicMaterial(topic_id=topic.id, material_id=mid))
    db.flush()
