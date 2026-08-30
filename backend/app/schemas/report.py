"""数据报告与推送骨架 Schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.report import (
    ReportGenerationStatus,
    ReportPushChannel,
    ReportPushRecordStatus,
    ReportPushRecipientType,
    ReportPushStatus,
    ReportReviewStatus,
    ReportType,
)
from app.core.enums import PromptStatus


class ReportTemplateCreate(BaseModel):
    report_type: ReportType
    name: str = Field(..., min_length=1, max_length=100)
    content_schema: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    status: PromptStatus = PromptStatus.启用


class ReportTemplateUpdate(BaseModel):
    report_type: ReportType | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    content_schema: dict[str, Any] | None = None
    is_default: bool | None = None
    status: PromptStatus | None = None


class ReportTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_type: ReportType
    name: str
    content_schema: dict[str, Any]
    is_default: bool
    status: PromptStatus
    created_by: int
    created_at: datetime
    updated_at: datetime


class ReportCreate(BaseModel):
    report_type: ReportType
    title: str | None = Field(None, max_length=500)
    period_start: datetime
    period_end: datetime
    template_id: int | None = None
    source_config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("周期结束不能早于开始")
        return self


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_no: str
    report_type: ReportType
    title: str
    period_start: datetime
    period_end: datetime
    template_id: int | None = None
    source_config: dict[str, Any]
    source_snapshot: dict[str, Any] | None = None
    summary: str
    content: str
    sections: dict[str, Any] | None = None
    conclusions: dict[str, Any] | None = None
    generation_trace: dict[str, Any] | None = None
    raw_ai_response: str | None = None
    is_ai_product: bool
    generation_status: ReportGenerationStatus
    review_status: ReportReviewStatus
    retry_count: int
    error_code: str | None = None
    error_message: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    generated_at: datetime | None = None


class ReportPushTaskCreate(BaseModel):
    channel: ReportPushChannel
    recipient_type: ReportPushRecipientType = ReportPushRecipientType.指定人
    target_object: str = Field(..., min_length=1, max_length=255)
    message_config: dict[str, Any] | None = None


class ReportPushRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    push_task_id: int
    channel: ReportPushChannel
    target_object: str
    recipient_type: ReportPushRecipientType
    message_summary: str
    sent_at: datetime | None = None
    status: ReportPushRecordStatus
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    response_snapshot: dict[str, Any] | None = None
    attempt_no: int
    created_at: datetime


class ReportPushTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_no: str
    report_id: int
    channel: ReportPushChannel
    recipient_type: ReportPushRecipientType
    target_object: str
    message_config: dict[str, Any] | None = None
    authorization_snapshot: dict[str, Any] | None = None
    status: ReportPushStatus
    retry_count: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    records: list[ReportPushRecordOut] = Field(default_factory=list)
