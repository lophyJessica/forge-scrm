"""选题库 Schema（模块 02）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ScreeningResult, Specialty, TopicStatus


class TopicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    direction: str = Field(..., min_length=1, max_length=50)
    specialty: Specialty
    customer_scenario: str = Field(..., min_length=1, max_length=200)
    user_perspective: str = Field(..., min_length=1, max_length=200)
    business_direction: str = Field(..., min_length=1, max_length=100)
    core_angle: str = Field(..., min_length=1, max_length=500)
    topic_principle: str = Field(..., min_length=1, max_length=200)
    topic_angle: str = Field(..., min_length=1, max_length=200)


class TopicCreate(TopicBase):
    material_ids: list[int] = Field(default_factory=list, description="可选参考资料引用（追溯非强制）")


class TopicUpdate(BaseModel):
    """人工修改选题：直接更新当前内容，一期不生成版本历史（D8）。"""

    title: str | None = Field(None, min_length=1, max_length=200)
    direction: str | None = Field(None, min_length=1, max_length=50)
    specialty: Specialty | None = None
    customer_scenario: str | None = Field(None, min_length=1, max_length=200)
    user_perspective: str | None = Field(None, min_length=1, max_length=200)
    business_direction: str | None = Field(None, min_length=1, max_length=100)
    core_angle: str | None = Field(None, min_length=1, max_length=500)
    topic_principle: str | None = Field(None, min_length=1, max_length=200)
    topic_angle: str | None = Field(None, min_length=1, max_length=200)
    material_ids: list[int] | None = None


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    direction: str
    specialty: Specialty
    customer_scenario: str
    user_perspective: str
    business_direction: str
    core_angle: str
    topic_principle: str
    topic_angle: str
    status: TopicStatus
    batch_no: str | None = None
    prompt_version_snapshot: dict | None = None
    has_ai_raw_response: bool = False
    screening_result: ScreeningResult | None = None
    created_by: int
    created_at: datetime
    material_ids: list[int] = []


class TopicGenerateRequest(BaseModel):
    direction: str = Field(..., min_length=1, max_length=50, description="本次生成的业务方向")
    specialty: Specialty
    material_ids: list[int] = Field(default_factory=list, description="参考资料（已生效资料）")
    prompt_template_id: int | None = Field(None, description="可选提示词模板；不传用内置默认模板")
    prompt_content: str | None = Field(None, min_length=1, description="自定义提示词，优先于模板和内置")
    count: int = Field(10, ge=1, le=10, description="R4：每方向 10 条")


class TopicGenerateResult(BaseModel):
    batch_no: str
    requested: int
    generated: int = Field(..., description="AI 返回条数")
    deduped: int = Field(..., description="被完全重复去重过滤掉的条数（同批次内 + 跨批次）")
    saved: int
    topics: list[TopicOut]
    ai_raw_archive: str = Field("", description="AI 原始响应留档路径")


class TopicBatchOut(BaseModel):
    """生成历史（M12）。"""

    batch_no: str
    direction: str
    count: int
    created_at: datetime
    created_by: int


class TopicScreenRequest(BaseModel):
    screening_result: ScreeningResult = Field(..., description="选中→已选定；淘汰→已废弃")
