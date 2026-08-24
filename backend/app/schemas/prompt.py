"""提示词模板 Schema（context/05 §4.3）。一期不建独立版本表，沿用 version 字段。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PromptStatus, PromptTaskType


class PromptTemplateCreate(BaseModel):
    task_type: PromptTaskType
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, description="提示词正文")
    material_combo: list[int] | None = Field(None, description="固定关联资料组合（资料 id 列表）")
    output_schema: dict | None = Field(None, description="输出字段定义；分析任务必填")
    status: PromptStatus = PromptStatus.启用


class PromptTemplateUpdate(BaseModel):
    """修改即版本号 +1（D9：一期不建 prompt_version 表）。"""

    name: str | None = Field(None, min_length=1, max_length=100)
    content: str | None = Field(None, min_length=1)
    material_combo: list[int] | None = None
    output_schema: dict | None = None
    status: PromptStatus | None = None


class PromptTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_type: PromptTaskType
    name: str
    content: str
    version: int | None = 1
    material_combo: list | None = None
    output_schema: dict | None = None
    status: PromptStatus | None = None
    created_by: int
    created_at: datetime
