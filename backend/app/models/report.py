"""数据报告与推送骨架。

字段对齐 prd-docs/modules/数据报告/数据报告字段清单.md。
新增实体/字段/枚举均为字段清单中的新增建议，待确认。
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, LongText, pk_column, utcnow


class ReportType(StrEnum):
    """报告类型；枚举新增建议，待确认。"""

    运营数据报告 = "运营数据报告"
    市场分析周报 = "市场分析周报"


class ReportGenerationStatus(StrEnum):
    """报告生成状态；状态新增建议，待确认。"""

    待生成 = "待生成"
    生成中 = "生成中"
    已完成 = "已完成"
    失败 = "失败"


class ReportReviewStatus(StrEnum):
    """报告审核/抽查状态；对齐总 PRD 5.3，状态新增建议，待确认。"""

    默认通过 = "默认通过"
    抽查中 = "抽查中"
    已确认 = "已确认"
    待审核 = "待审核"
    已废弃 = "已废弃"


class ReportPushChannel(StrEnum):
    """推送渠道；枚举新增建议，待确认。API/授权/频率待实测。"""

    飞书 = "飞书"
    微信 = "微信"


class ReportPushRecipientType(StrEnum):
    """推送目标类型；新增建议，待确认。"""

    指定人 = "指定人"
    群 = "群"


class ReportPushStatus(StrEnum):
    """推送任务/记录状态；新增建议，待确认。"""

    待推送 = "待推送"
    推送中 = "推送中"
    已推送 = "已推送"
    失败 = "失败"
    已取消 = "已取消"


def _updated_at_column():
    return mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow, comment="修改时间")


class Report(Base):
    __tablename__ = "report"
    __table_args__ = (
        Index("idx_report_type_status", "report_type", "generation_status"),
        Index("idx_report_created_at", "created_at"),
        Index("idx_report_period", "period_start", "period_end"),
    )

    id: Mapped[int] = pk_column()
    report_no: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="报告编号；新增建议，待确认"
    )
    report_type: Mapped[ReportType] = mapped_column(
        enum_type(ReportType, "report_type"),
        nullable=False,
        comment="运营数据报告/市场分析周报；枚举新增建议，待确认",
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="报告标题；复用资料标题语义，映射新增建议，待确认"
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告周期开始；周期口径新增建议，待确认"
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="报告周期结束；周期口径新增建议，待确认"
    )
    template_id: Mapped[int | None] = mapped_column(
        BigInt, nullable=True, comment="使用的报告模板；新增建议，待确认。本期模板实体未展开"
    )
    source_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="来源实体、时间窗和口径配置；新增建议，待确认"
    )
    source_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="生成时来源摘要/快照（含类型与id）；新增建议，待确认"
    )
    summary: Mapped[str] = mapped_column(
        LongText, nullable=False, default="", comment="报告摘要；报告字段映射新增建议，待确认"
    )
    content: Mapped[str] = mapped_column(
        LongText, nullable=False, default="", comment="报告正文；报告字段映射新增建议，待确认"
    )
    sections: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="章节、数据表和结论结构；新增建议，待确认"
    )
    conclusions: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="结构化结论与建议；新增建议，待确认"
    )
    generation_trace: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="生成输入、模型/提示词快照、时间和版本；新增建议，待确认"
    )
    raw_ai_response: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="AI 原始响应；沿用一期留档语义，映射新增建议，待确认"
    )
    is_ai_product: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1", comment="AI 产物标记；对齐 R8，报告属 AI 产物"
    )
    generation_status: Mapped[ReportGenerationStatus] = mapped_column(
        enum_type(ReportGenerationStatus, "report_generation_status"),
        nullable=False,
        default=ReportGenerationStatus.待生成,
        comment="待生成/生成中/已完成/失败；状态新增建议，待确认",
    )
    review_status: Mapped[ReportReviewStatus] = mapped_column(
        enum_type(ReportReviewStatus, "report_review_status"),
        nullable=False,
        default=ReportReviewStatus.默认通过,
        comment="默认通过/抽查中/已确认/待审核/已废弃；新增建议，待确认",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="生成重试次数；新增建议，待确认"
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="生成失败错误码；新增建议，待确认"
    )
    error_message: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="生成失败说明；新增建议，待确认"
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人；复用创建追踪语义"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = _updated_at_column()
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="报告生成完成时间；新增建议，待确认"
    )

    push_tasks: Mapped[list["ReportPushTask"]] = relationship(
        "ReportPushTask", back_populates="report", cascade="all, delete-orphan"
    )


class ReportPushTask(Base):
    __tablename__ = "report_push_task"
    __table_args__ = (
        Index("idx_report_push_task_report", "report_id"),
        Index("idx_report_push_task_status", "status"),
    )

    id: Mapped[int] = pk_column()
    task_no: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="推送任务编号；新增建议，待确认"
    )
    report_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("report.id", ondelete="CASCADE"), nullable=False, comment="关联已完成报告；新增建议，待确认"
    )
    channel: Mapped[ReportPushChannel] = mapped_column(
        enum_type(ReportPushChannel, "report_push_channel"),
        nullable=False,
        comment="飞书/微信；渠道枚举新增建议，待确认。API 待实测",
    )
    recipient_type: Mapped[ReportPushRecipientType] = mapped_column(
        enum_type(ReportPushRecipientType, "report_push_recipient_type"),
        nullable=False,
        default=ReportPushRecipientType.指定人,
        comment="指定人/群；目标类型新增建议，待确认",
    )
    target_object: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="目标人或群标识；新增建议，待确认"
    )
    message_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="摘要/正文/链接/卡片配置；新增建议，待确认"
    )
    authorization_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="授权校验结果，不保存凭据；新增建议，待确认"
    )
    status: Mapped[ReportPushStatus] = mapped_column(
        enum_type(ReportPushStatus, "report_push_status"),
        nullable=False,
        default=ReportPushStatus.待推送,
        comment="待推送/推送中/已推送/失败/已取消；状态新增建议，待确认",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="任务重试次数；新增建议，待确认"
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人；新增建议，待确认"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = _updated_at_column()

    report: Mapped["Report"] = relationship("Report", back_populates="push_tasks")
    records: Mapped[list["ReportPushRecord"]] = relationship(
        "ReportPushRecord", back_populates="push_task", cascade="all, delete-orphan"
    )


class ReportPushRecord(Base):
    __tablename__ = "report_push_record"
    __table_args__ = (Index("idx_report_push_record_task", "push_task_id"),)

    id: Mapped[int] = pk_column()
    push_task_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("report_push_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联推送任务；新增建议，待确认",
    )
    channel: Mapped[ReportPushChannel] = mapped_column(
        enum_type(ReportPushChannel, "report_push_record_channel"),
        nullable=False,
        comment="目标渠道：飞书/微信；枚举新增建议，待确认",
    )
    target_object: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="实际目标人或群标识；新增建议，待确认"
    )
    recipient_type: Mapped[ReportPushRecipientType] = mapped_column(
        enum_type(ReportPushRecipientType, "report_push_record_recipient_type"),
        nullable=False,
        comment="人/群；新增建议，待确认",
    )
    message_summary: Mapped[str] = mapped_column(
        LongText, nullable=False, comment="实际发送的消息摘要；必须保留，新增字段建议，待确认"
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="实际发送时间；必须保留，新增字段建议，待确认"
    )
    status: Mapped[ReportPushStatus] = mapped_column(
        enum_type(ReportPushStatus, "report_push_record_status"),
        nullable=False,
        default=ReportPushStatus.待推送,
        comment="待推送/推送中/已推送/失败/已取消；新增建议，待确认",
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="渠道返回消息 ID；新增建议，待确认"
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="失败时的渠道错误码；必须保留，新增字段建议，待确认"
    )
    error_message: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="失败时错误说明；新增建议，待确认"
    )
    response_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="渠道响应摘要，不保存敏感凭据；新增建议，待确认"
    )
    attempt_no: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="发送尝试序号；新增建议，待确认"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, comment="记录创建时间")

    push_task: Mapped["ReportPushTask"] = relationship("ReportPushTask", back_populates="records")
