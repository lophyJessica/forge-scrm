"""二期自动采集与研究助手骨架 Schema。

本文件只描述 CRUD 输入输出；执行、重试和 AI/采集逻辑由后续步骤实现。
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import ContentElement, ScriptStyle, Specialty, TrustLevel
from app.models.phase2 import (
    CollectionRecordStatus,
    CollectionTaskStatus,
    PushStatus,
    ResearchReportStatus,
    ResearchTaskStatus,
)


_RESEARCH_SCOPE_TYPES = {
    "资料库",
    "material",
    "materials",
    "自动采集结果",
    "collection_result",
    "collection_results",
    "外部检索",
    "external_search",
}


def _validate_research_scope(scope_config: dict[str, Any]) -> None:
    raw = scope_config.get("source_types") if isinstance(scope_config, dict) else None
    if raw is None:
        return  # 旧任务仅含 query/max_results 等字段，保持兼容
    if not isinstance(raw, list) or not raw:
        raise ValueError("source_types 必须是非空数组")
    unknown = [value for value in raw if not isinstance(value, str) or value not in _RESEARCH_SCOPE_TYPES]
    if unknown:
        raise ValueError(f"不支持的研究来源类型：{unknown}")


class BenchmarkAccountCreate(BaseModel):
    platform: str = Field(..., min_length=1, max_length=32)
    account_identifier: str = Field(..., min_length=1, max_length=255)
    account_name: str | None = Field(None, max_length=255)
    profile_url: str | None = Field(None, max_length=1000)
    benchmark_flag: bool = True
    enabled: bool = True
    notes: str | None = None


class BenchmarkAccountUpdate(BaseModel):
    platform: str | None = Field(None, min_length=1, max_length=32)
    account_identifier: str | None = Field(None, min_length=1, max_length=255)
    account_name: str | None = Field(None, max_length=255)
    profile_url: str | None = Field(None, max_length=1000)
    benchmark_flag: bool | None = None
    enabled: bool | None = None
    notes: str | None = None


class BenchmarkAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    account_identifier: str
    account_name: str | None = None
    profile_url: str | None = None
    benchmark_flag: bool
    enabled: bool
    notes: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    last_collected_at: datetime | None = None


class CollectionTaskCreate(BaseModel):
    task_no: str | None = Field(None, min_length=1, max_length=64)
    trigger_type: str = Field("manual", min_length=1, max_length=32)
    scope_type: str = Field("benchmark_account", min_length=1, max_length=64)
    scope_config: dict[str, Any] = Field(default_factory=dict)
    time_window_start: datetime
    time_window_end: datetime

    @model_validator(mode="after")
    def validate_window(self):
        if self.time_window_end < self.time_window_start:
            raise ValueError("时间窗结束不能早于开始")
        return self


class CollectionTaskUpdate(BaseModel):
    scope_type: str | None = Field(None, min_length=1, max_length=64)
    scope_config: dict[str, Any] | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self):
        if self.time_window_start and self.time_window_end and self.time_window_end < self.time_window_start:
            raise ValueError("时间窗结束不能早于开始")
        return self


class CollectionTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_no: str
    trigger_type: str
    status: CollectionTaskStatus
    scope_type: str
    scope_config: dict[str, Any]
    time_window_start: datetime
    time_window_end: datetime
    requested_by: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_count: int
    success_count: int
    failure_count: int
    retry_count: int
    error_message: str | None = None
    idempotency_key: str | None = None
    created_at: datetime


class CollectionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    benchmark_account_id: int | None = None
    source_type: str
    source_url: str | None = None
    status: CollectionRecordStatus
    attempt_no: int
    requested_at: datetime
    completed_at: datetime | None = None
    raw_response: str | None = None
    http_status: int | None = None
    item_count: int
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool


class CollectionResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    task_id: int
    benchmark_account_id: int | None = None
    business_object: str
    platform: str | None = None
    account_identifier: str | None = None
    is_benchmark: bool
    source_url: str | None = None
    raw_content: str
    structured_data: dict[str, Any] | None = None
    collected_at: datetime
    window_start: datetime
    window_end: datetime
    data_cleaning_note: str | None = None
    is_ai_product: bool
    ai_derivative_id: int | None = None
    created_at: datetime


class CollectionResultMaterialCreate(BaseModel):
    """采集结果沉淀资料时允许用户确认的资料字段。"""

    title: str | None = Field(None, min_length=1, max_length=200)
    class_id: int
    tags: list[str] = Field(default_factory=list)
    trust_level: TrustLevel = TrustLevel.中
    valid_from: date = Field(default_factory=date.today)
    valid_until: date = Field(default_factory=lambda: date.today() + timedelta(days=365))

    @model_validator(mode="after")
    def validate_window(self):
        if self.valid_until < self.valid_from:
            raise ValueError("有效期止不能早于开始")
        return self


class ResearchTaskCreate(BaseModel):
    task_no: str | None = Field(None, min_length=1, max_length=64)
    topic: str = Field(..., min_length=1, max_length=500)
    objective: str = Field(..., min_length=1)
    scope_config: dict[str, Any] = Field(default_factory=dict)
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self):
        if self.time_window_start and self.time_window_end and self.time_window_end < self.time_window_start:
            raise ValueError("时间窗结束不能早于开始")
        _validate_research_scope(self.scope_config)
        return self


class ResearchTaskUpdate(BaseModel):
    topic: str | None = Field(None, min_length=1, max_length=500)
    objective: str | None = Field(None, min_length=1)
    scope_config: dict[str, Any] | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self):
        if self.time_window_start and self.time_window_end and self.time_window_end < self.time_window_start:
            raise ValueError("时间窗结束不能早于开始")
        if self.scope_config is not None:
            _validate_research_scope(self.scope_config)
        return self


class ResearchTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_no: str
    topic: str
    objective: str
    scope_config: dict[str, Any]
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    status: ResearchTaskStatus
    current_stage: str | None = None
    progress_percent: Decimal | None = None
    progress_message: str | None = None
    checkpoint_data: dict[str, Any] | None = None
    retry_count: int
    last_error_code: str | None = None
    last_error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    requested_by: int
    created_at: datetime
    updated_at: datetime


class ResearchReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    research_task_id: int
    title: str
    summary: str
    content: str
    sections: dict[str, Any] | None = None
    conclusions: dict[str, Any] | None = None
    generation_trace: dict[str, Any] | None = None
    raw_ai_response: str | None = None
    is_ai_product: bool
    status: ResearchReportStatus
    source_count: int
    created_at: datetime
    updated_at: datetime


class ResearchReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    source_kind: str
    source_url: str | None = None
    source_title: str | None = None
    search_provider: str | None = None
    collection_result_id: int | None = None
    material_id: int | None = None
    source_snapshot: str | None = None
    page_number: str | None = None
    paragraph_locator: str | None = None
    evidence_summary: str | None = None
    source_type: str | None = None
    cited_at: datetime
    created_at: datetime


class ResearchMaterializeRequest(BaseModel):
    class_id: int
    trust_level: TrustLevel = TrustLevel.中
    valid_from: date = Field(default_factory=date.today)
    valid_until: date = Field(default_factory=lambda: date.today() + timedelta(days=365))
    section_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.valid_until < self.valid_from:
            raise ValueError("有效期止不能早于有效期起")
        return self


class ResearchMaterializeResult(BaseModel):
    material_ids: list[int]
    materials: list[dict[str, Any]] = Field(default_factory=list)


class ResearchTopicGenerateRequest(BaseModel):
    direction: str = Field(..., min_length=1, max_length=50)
    specialty: Specialty
    count: int = Field(10, ge=1, le=10)
    material_ids: list[int] = Field(default_factory=list)
    prompt_template_id: int | None = None
    prompt_content: str | None = Field(None, min_length=1)


class ResearchScriptGenerateRequest(BaseModel):
    topic_id: int
    style: ScriptStyle
    content_elements: list[ContentElement] = Field(default_factory=list)
    version_count: int = Field(3, ge=2, le=3)
    material_ids: list[int] = Field(default_factory=list)
    prompt_template_id: int | None = None
    prompt_content: str | None = Field(None, min_length=1)
