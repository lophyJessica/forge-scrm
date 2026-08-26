"""脚本库 Schema（模块 03）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ContentElement, ScriptStatus, ScriptStyle


class ScriptCreate(BaseModel):
    """独立创建脚本（R9/R10：topic_id 可空、可后补关联）。"""

    topic_id: int | None = None
    content: str = Field(..., min_length=1, description="脚本正文，服务端校验非空")
    style: ScriptStyle
    content_elements: list[ContentElement] = Field(default_factory=list)
    material_refs: list[int] | None = None


class ScriptUpdate(BaseModel):
    """修改脚本 → 产生新版本（R11）。"""

    content: str | None = Field(None, min_length=1)
    style: ScriptStyle | None = None
    content_elements: list[ContentElement] | None = None
    topic_id: int | None = Field(None, description="独立创建后补录选题关联")
    note: str | None = Field(None, max_length=200, description="修改备注（⚠️ 新增建议字段）")


class ScriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int | None = None
    topic_title: str | None = None
    content: str
    style: ScriptStyle
    content_elements: list[str] = []
    current_version: int
    status: ScriptStatus
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    created_by: int
    created_at: datetime
    modified_by: int
    modified_at: datetime
    material_refs: list[int] | None = None
    prompt_version_snapshot: dict | None = None


class ScriptVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    script_id: int
    version: int
    content_snapshot: str
    changed_by: int
    changed_at: datetime
    note: str | None = None


class ScriptGenerateRequest(BaseModel):
    """基于选题生成 2-3 版脚本（R5）。"""

    topic_id: int = Field(..., description="R10：基于选题创建时必填")
    style: ScriptStyle
    content_elements: list[ContentElement] = Field(default_factory=list)
    version_count: int = Field(3, ge=2, le=3, description="R5：每选题 2-3 版")
    material_ids: list[int] = Field(default_factory=list, description="可选资料追溯")
    prompt_template_id: int | None = None
    prompt_content: str | None = Field(None, min_length=1, description="自定义提示词，优先于模板和内置")


class ScriptGenerateResult(BaseModel):
    topic_id: int
    generated: int
    scripts: list[ScriptOut]
    ai_raw_archive: str = ""


class ScriptReview(BaseModel):
    approved: bool = Field(..., description="true=通过（已通过）；false=驳回（已废弃）")


class ScriptRollbackRequest(BaseModel):
    version: int = Field(..., ge=1, description="回退到的历史版本号")


class ScriptDiffOut(BaseModel):
    left_version: int
    right_version: int
    left_content: str
    right_content: str
    diff: str = Field(..., description="统一 diff 文本，前端可直接展示")
