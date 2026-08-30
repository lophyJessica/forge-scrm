"""数据分析 Schema（模块 04：数据源 / 原始数据 / 分析任务 / 分析结果 / 回写反哺）。"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import (
    AnalysisTaskStatus,
    AnalysisTaskType,
    BusinessObject,
    CollectionMethod,
    DataSourceStatus,
    Platform,
    SourceType,
    TrustLevel,
    WritebackMaterialStatus,
    WritebackTopicStatus,
)


# ---------------- 数据源 ----------------

class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    collection_method: CollectionMethod = Field(
        CollectionMethod.手动录入, description="D5：一期仅手动录入 / CSV 导入"
    )
    business_object: BusinessObject
    platform: Platform | None = None
    account_identifier: str | None = Field(None, max_length=200, description="账号类数据必填")
    is_benchmark: bool = False
    config: dict | None = None
    status: DataSourceStatus = DataSourceStatus.启用


class DataSourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    collection_method: CollectionMethod | None = None
    business_object: BusinessObject | None = None
    platform: Platform | None = None
    account_identifier: str | None = Field(None, max_length=200)
    is_benchmark: bool | None = None
    config: dict | None = None
    status: DataSourceStatus | None = None


class DataSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    collection_method: CollectionMethod
    business_object: BusinessObject
    platform: Platform | None = None
    account_identifier: str | None = None
    is_benchmark: bool
    config: dict | None = None
    status: DataSourceStatus | None = None


# ---------------- 原始数据 ----------------

class RawDataCreate(BaseModel):
    source_id: int
    raw_content: str = Field(..., min_length=1, description="原始内容")
    structured: dict | None = Field(None, description="D6：一期仅通用基础结构")
    collected_at: datetime | None = None
    window_start: datetime
    window_end: datetime
    clean_dedup_record: dict = Field(default_factory=dict)


class RawDataUpdate(BaseModel):
    raw_content: str | None = Field(None, min_length=1)
    structured: dict | None = None
    collected_at: datetime | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    clean_dedup_record: dict | None = None


class RawDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    source_name: str | None = None
    collected_at: datetime
    raw_content: str | None = None
    structured: dict | None = None
    window_start: datetime
    window_end: datetime
    clean_dedup_record: dict = {}


# ---------------- 分析任务 ----------------

class AnalysisTaskCreate(BaseModel):
    name: str | None = Field(None, max_length=100)
    type: AnalysisTaskType
    raw_data_ids: list[int] = Field(default_factory=list, description="分析输入的原始数据")
    collection_result_ids: list[int] = Field(default_factory=list, description="分析输入的自动采集结果")
    prompt_template_id: int | None = Field(None, description="提示词模板；缺省用内置模板")
    material_ids: list[int] = Field(default_factory=list, description="资料库上下文快照来源")
    output_schema: dict | None = Field(None, description="输出字段定义；缺省用内置结构")

    @model_validator(mode="after")
    def validate_inputs(self):
        if not self.raw_data_ids and not self.collection_result_ids:
            raise ValueError("至少选择一项分析输入")
        return self


class AnalysisResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    result_content: dict = {}
    writeback_material_status: WritebackMaterialStatus
    writeback_topic_status: WritebackTopicStatus
    material_ids: list[int] = []
    topic_ids: list[int] = []


class AnalysisTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    type: AnalysisTaskType
    status: AnalysisTaskStatus
    prompt_version_snapshot: dict | None = None
    material_context_snapshot: dict | None = None
    output_schema: dict = {}
    has_ai_raw_response: bool = False
    error_message: str | None = None
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    created_by: int
    created_at: datetime
    retry_count: int | None = 0
    raw_data_ids: list[int] = []
    collection_result_ids: list[int] = []
    results: list[AnalysisResultOut] = []


class AnalysisTaskReview(BaseModel):
    approved: bool = Field(..., description="true=确认（已确认）；false=驳回（已废弃）")


# ---------------- 回写 / 反哺 ----------------

class WritebackMaterialItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    class_id: int
    source_type: SourceType = SourceType.报告
    trust_level: TrustLevel = TrustLevel.中
    valid_from: date
    valid_until: date
    tags: list[str] = Field(default_factory=list)


class WritebackMaterialRequest(BaseModel):
    """回写资料库（独立动作）；回写产物为草稿，需按 R1 走审核。"""

    materials: list[WritebackMaterialItem] = Field(..., min_length=1)


class WritebackTopicItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    direction: str = Field(..., min_length=1, max_length=100)
    specialty: str
    customer_scenario: str
    user_perspective: str
    business_direction: str
    core_angle: str
    topic_principle: str
    topic_angle: str


class WritebackTopicRequest(BaseModel):
    """反哺选题库（独立动作）；产物为「待筛选」，需按 R3 人工筛选。"""

    topics: list[WritebackTopicItem] = Field(..., min_length=1)


class RawDataImportResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: list[dict] = []
    stored_file: str = ""
