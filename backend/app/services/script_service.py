"""脚本服务：版本链维护、DeepSeek 脚本生成、输出装配。"""

import difflib
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MaterialStatus, PromptStatus, PromptTaskType, ScriptStyle
from app.core.exceptions import BizError
from app.models.material import Material
from app.models.prompt import PromptTemplate
from app.models.script import Script, ScriptVersion
from app.models.topic import Topic
from app.schemas.script import ScriptOut

DEFAULT_SYSTEM_PROMPT = (
    "你是资深口播脚本撰稿人，服务对象是面向中小微企业主的企业线上营销与获客账号。"
    "请严格输出 JSON 对象，不要输出任何解释文字。"
)

DEFAULT_USER_PROMPT_TEMPLATE = """请基于以下选题撰写 {count} 个不同版本的口播脚本。

选题信息：
- 标题：{title}
- 方向：{direction}
- 专业方向：{specialty}
- 结合场景：{customer_scenario}
- 用户视角：{user_perspective}
- 经营方向：{business_direction}
- 核心角度：{core_angle}
- 选题原则：{topic_principle}
- 选题角度：{topic_angle}

语言风格：{style}
必须包含的内容要素：{elements}

{material_block}

输出 JSON 格式（严格遵守，scripts 数组长度为 {count}）：
{{
  "scripts": [
    {{"content": "完整脚本正文"}}
  ]
}}

要求：
1. {count} 个版本表达角度不同，不得重复；
2. content 必须是非空中文正文，不少于 200 字；
3. 严格贴合「{style}」的语言风格；
4. 只输出 JSON。"""


def validate_scripts_payload(count: int):
    def _validate(data: Any) -> list[str]:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("scripts")
        else:
            raise ValueError("AI 输出不是 JSON 对象或数组")
        if not isinstance(items, list) or not items:
            raise ValueError("AI 输出缺少非空的 scripts 数组")
        contents: list[str] = []
        for idx, item in enumerate(items, start=1):
            content = item.get("content") if isinstance(item, dict) else item
            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"第 {idx} 版脚本正文为空")
            contents.append(content.strip())
        return contents

    return _validate


def build_prompt(
    db: Session,
    topic: Topic,
    style: ScriptStyle,
    elements: list[str],
    count: int,
    material_ids: list[int],
    template_id: int | None,
    prompt_content: str | None = None,
) -> tuple[str, str, dict | None]:
    material_block = "本次不提供参考资料。"
    if material_ids:
        rows = list(db.scalars(select(Material).where(Material.id.in_(material_ids))).all())
        invalid = [r.title for r in rows if r.status != MaterialStatus.已生效]
        if invalid:
            raise BizError(f"参考资料必须为「已生效」状态（R1）：{'、'.join(invalid)}")
        material_block = "参考资料：\n" + "\n".join(
            f"- {r.title}：{r.content[:500]}" for r in rows
        )

    custom_prompt = (prompt_content or "").strip()
    if custom_prompt:
        system_prompt = custom_prompt
        snapshot = {
            "prompt_type": "custom",
            "content": custom_prompt,
        }
    else:
        template = db.get(PromptTemplate, template_id) if template_id is not None else db.scalar(
            select(PromptTemplate)
            .where(PromptTemplate.task_type == PromptTaskType.脚本生成, PromptTemplate.status == PromptStatus.启用)
            .order_by(PromptTemplate.id.asc())
        )
        if template is not None:
            system_prompt = template.content
            snapshot = {
                "template_id": template.id,
                "name": template.name,
                "version": template.version,
                "content_snapshot": template.content,
            }
        else:
            system_prompt = DEFAULT_SYSTEM_PROMPT
            snapshot = {
                "template_id": None,
                "name": "内置脚本生成提示词",
                "version": 0,
                "content_snapshot": DEFAULT_SYSTEM_PROMPT,
            }

    user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(
        count=count,
        title=topic.title,
        direction=topic.direction,
        specialty=topic.specialty.value,
        customer_scenario=topic.customer_scenario,
        user_perspective=topic.user_perspective,
        business_direction=topic.business_direction,
        core_angle=topic.core_angle,
        topic_principle=topic.topic_principle,
        topic_angle=topic.topic_angle,
        style=style.value,
        elements="、".join(elements) if elements else "不限",
        material_block=material_block,
    )
    return system_prompt, user_prompt, snapshot


def add_version(
    db: Session, script: Script, content: str, changed_by: int, note: str | None
) -> ScriptVersion:
    """写入一条版本快照（R11：每次修改生成新版本）。"""
    version = ScriptVersion(
        script_id=script.id,
        version=script.current_version,
        content_snapshot=content,
        changed_by=changed_by,
        note=note,
    )
    db.add(version)
    db.flush()
    return version


def to_out(db: Session, script: Script) -> ScriptOut:
    out = ScriptOut.model_validate(script)
    if script.topic_id:
        topic = db.get(Topic, script.topic_id)
        out.topic_title = topic.title if topic else None
    out.content_elements = list(script.content_elements or [])
    return out


def make_diff(left: ScriptVersion, right: ScriptVersion) -> str:
    diff = difflib.unified_diff(
        (left.content_snapshot or "").splitlines(),
        (right.content_snapshot or "").splitlines(),
        fromfile=f"v{left.version}",
        tofile=f"v{right.version}",
        lineterm="",
    )
    return "\n".join(diff)
