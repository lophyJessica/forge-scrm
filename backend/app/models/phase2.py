"""二期自动采集与研究助手数据骨架。

本文件只定义数据模型，不实现采集执行、联网检索、AI 生成或推送逻辑。
字段与二期字段清单对应；字段清单中标注待确认的建议字段在此保留 TODO(待确认)。
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, LongText, pk_column, utcnow


class CollectionTaskStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    partial_success = "partial_success"
    failed = "failed"


class CollectionRecordStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class ResearchTaskStatus(StrEnum):
    pending = "pending"
    searching = "searching"
    organizing = "organizing"
    success = "success"
    failed = "failed"


class ResearchReportStatus(StrEnum):
    success = "success"
    failed = "failed"
    discarded = "discarded"


class PushStatus(StrEnum):
    pending = "pending"
    sending = "sending"
    sent = "sent"
    failed = "failed"


def _updated_at_column():
    """与一期时间字段风格一致的可自动更新时间字段。"""

    return mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow, comment="修改时间")


def _phase2_created_at_column():
    return mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
        comment="创建时间；TODO(待确认)：技术字段映射",
    )


class BenchmarkAccount(Base):
    __tablename__ = "benchmark_account"
    __table_args__ = (
        Index("idx_benchmark_account_platform", "platform"),
        Index("idx_benchmark_account_enabled", "enabled"),
    )

    id: Mapped[int] = pk_column()
    platform: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="平台；TODO(待确认)：最终平台枚举和接口范围"
    )
    account_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="平台账号标识；TODO(待确认)：字段映射"
    )
    account_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="页面展示名称；TODO(待确认)"
    )
    profile_url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="账号主页 URL；TODO(待确认)"
    )
    benchmark_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否对标账号；复用 context/05 语义；TODO(待确认)：字段映射"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否允许新任务选择；TODO(待确认)"
    )
    notes: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="操盘手备注；TODO(待确认)"
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人；TODO(待确认)：外键映射"
    )
    created_at: Mapped[datetime] = _phase2_created_at_column()
    updated_at: Mapped[datetime] = _updated_at_column()
    last_collected_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近采集时间；TODO(待确认)"
    )

    records: Mapped[list["CollectionRecord"]] = relationship(
        "CollectionRecord", back_populates="benchmark_account"
    )
    results: Mapped[list["CollectionResult"]] = relationship(
        "CollectionResult", back_populates="benchmark_account"
    )


class CollectionTask(Base):
    __tablename__ = "collection_task"
    __table_args__ = (
        Index("idx_collection_task_status", "status"),
        Index("idx_collection_task_created_at", "created_at"),
        Index("idx_collection_task_idempotency_key", "idempotency_key"),
    )

    id: Mapped[int] = pk_column()
    task_no: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="任务编号；TODO(待确认)"
    )
    trigger_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", comment="触发方式；P0 仅 manual；TODO(待确认)"
    )
    status: Mapped[CollectionTaskStatus] = mapped_column(
        enum_type(CollectionTaskStatus, "collection_task_status"),
        nullable=False,
        default=CollectionTaskStatus.pending,
        comment="pending/running/success/partial_success/failed；TODO(待确认)：正式枚举落库",
    )
    scope_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="benchmark_account", comment="采集范围类型；TODO(待确认)"
    )
    scope_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="账号集合、来源和范围配置；TODO(待确认)"
    )
    time_window_start: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="采集时间窗开始；TODO(待确认)：时间窗映射"
    )
    time_window_end: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="采集时间窗结束；TODO(待确认)：时间窗映射"
    )
    requested_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="发起人；TODO(待确认)"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="实际开始时间；TODO(待确认)"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="实际结束时间；TODO(待确认)"
    )
    total_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="记录总数；TODO(待确认)"
    )
    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="成功记录数；TODO(待确认)"
    )
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="失败记录数；TODO(待确认)"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="任务级重试次数；TODO(待确认)"
    )
    error_message: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="任务级错误；TODO(待确认)"
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="同账号/时间窗/范围幂等键；TODO(待确认)"
    )
    created_at: Mapped[datetime] = _phase2_created_at_column()

    records: Mapped[list["CollectionRecord"]] = relationship(
        "CollectionRecord", back_populates="task", cascade="all, delete-orphan"
    )
    results: Mapped[list["CollectionResult"]] = relationship(
        "CollectionResult", back_populates="task", cascade="all, delete-orphan"
    )


class CollectionRecord(Base):
    __tablename__ = "collection_record"
    __table_args__ = (Index("idx_collection_record_task_status", "task_id", "status"),)

    id: Mapped[int] = pk_column()
    task_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("collection_task.id", ondelete="CASCADE"), nullable=False, comment="关联采集任务；TODO(待确认)"
    )
    benchmark_account_id: Mapped[int | None] = mapped_column(
        BigInt, ForeignKey("benchmark_account.id"), nullable=True, comment="关联对标账号；TODO(待确认)"
    )
    source_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="benchmark_account", comment="来源类型；TODO(待确认)：不得与资料 source_type 混用"
    )
    source_url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="来源 URL；TODO(待确认)"
    )
    status: Mapped[CollectionRecordStatus] = mapped_column(
        enum_type(CollectionRecordStatus, "collection_record_status"),
        nullable=False,
        default=CollectionRecordStatus.pending,
        comment="pending/running/success/failed；TODO(待确认)",
    )
    attempt_no: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="当前尝试序号；TODO(待确认)"
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, comment="请求时间；TODO(待确认)"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完成时间；TODO(待确认)"
    )
    raw_response: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="来源原始响应；TODO(待确认)：json/text 存储方式"
    )
    http_status: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="来源响应状态；TODO(待确认)"
    )
    item_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="本次得到的条目数；TODO(待确认)"
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="结构化错误码；TODO(待确认)"
    )
    error_message: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="记录级错误原因；TODO(待确认)"
    )
    retryable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否允许重试；TODO(待确认)"
    )

    task: Mapped["CollectionTask"] = relationship("CollectionTask", back_populates="records")
    benchmark_account: Mapped["BenchmarkAccount | None"] = relationship(
        "BenchmarkAccount", back_populates="records"
    )
    results: Mapped[list["CollectionResult"]] = relationship(
        "CollectionResult", back_populates="record", cascade="all, delete-orphan"
    )


class CollectionResult(Base):
    __tablename__ = "collection_result"
    __table_args__ = (Index("idx_collection_result_task", "task_id"),)

    id: Mapped[int] = pk_column()
    record_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("collection_record.id", ondelete="CASCADE"), nullable=False, comment="关联采集记录；TODO(待确认)"
    )
    task_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("collection_task.id", ondelete="CASCADE"), nullable=False, comment="关联采集任务；TODO(待确认)"
    )
    benchmark_account_id: Mapped[int | None] = mapped_column(
        BigInt, ForeignKey("benchmark_account.id"), nullable=True, comment="关联对标账号；TODO(待确认)"
    )
    business_object: Mapped[str] = mapped_column(
        String(64), nullable=False, default="对标账号", comment="业务对象；复用 context/05 语义"
    )
    platform: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="平台；复用 context/05 语义；TODO(待确认)：具体值"
    )
    account_identifier: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="账号标识；复用 context/05 语义"
    )
    is_benchmark: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="对标标记；复用 context/05 语义"
    )
    source_url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="来源链接；复用 context/05 语义；TODO(待确认)"
    )
    raw_content: Mapped[str] = mapped_column(
        LongText, nullable=False, comment="原始数据内容；复用 context/05 语义；TODO(待确认)：json/text 存储方式"
    )
    structured_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="结构化数据；复用 context/05 语义；TODO(待确认)"
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="原始数据获取时间；复用 context/05 语义"
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="采集任务时间窗开始；复用 context/05 语义"
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="采集任务时间窗结束；复用 context/05 语义"
    )
    data_cleaning_note: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="数据清洗/去重记录；复用 context/05 语义；TODO(待确认)：json/text 存储方式"
    )
    is_ai_product: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否 AI 产物；采集结果默认 false"
    )
    ai_derivative_id: Mapped[int | None] = mapped_column(
        BigInt, nullable=True, comment="AI 摘要/分类衍生结果关联；TODO(待确认)"
    )
    created_at: Mapped[datetime] = _phase2_created_at_column()

    record: Mapped["CollectionRecord"] = relationship("CollectionRecord", back_populates="results")
    task: Mapped["CollectionTask"] = relationship("CollectionTask", back_populates="results")
    benchmark_account: Mapped["BenchmarkAccount | None"] = relationship(
        "BenchmarkAccount", back_populates="results"
    )


class ResearchTask(Base):
    __tablename__ = "research_task"
    __table_args__ = (
        Index("idx_research_task_status", "status"),
        Index("idx_research_task_created_at", "created_at"),
    )

    id: Mapped[int] = pk_column()
    task_no: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="研究任务编号；TODO(待确认)"
    )
    topic: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="研究主题；TODO(待确认)"
    )
    objective: Mapped[str] = mapped_column(
        LongText, nullable=False, comment="研究目标/问题；TODO(待确认)"
    )
    scope_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="外部检索、资料和采集结果范围；TODO(待确认)"
    )
    time_window_start: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="研究时间窗开始；TODO(待确认)"
    )
    time_window_end: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="研究时间窗结束；TODO(待确认)"
    )
    status: Mapped[ResearchTaskStatus] = mapped_column(
        enum_type(ResearchTaskStatus, "research_task_status"),
        nullable=False,
        default=ResearchTaskStatus.pending,
        comment="pending/searching/organizing/success/failed；TODO(待确认)：正式枚举落库",
    )
    current_stage: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="阶段信息；TODO(待确认)：可由执行中+阶段字段替代"
    )
    progress_percent: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True, comment="阶段进度百分比；TODO(待确认)"
    )
    progress_message: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="最近进度说明；TODO(待确认)"
    )
    checkpoint_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="可恢复游标和中间上下文；TODO(待确认)"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="任务重试次数；TODO(待确认)"
    )
    last_error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="最近错误码；TODO(待确认)"
    )
    last_error_message: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="最近错误说明；TODO(待确认)"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="开始时间；TODO(待确认)"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完成时间；TODO(待确认)"
    )
    requested_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人；TODO(待确认)"
    )
    created_at: Mapped[datetime] = _phase2_created_at_column()
    updated_at: Mapped[datetime] = _updated_at_column()

    report: Mapped["ResearchReport | None"] = relationship(
        "ResearchReport", back_populates="research_task", uselist=False, cascade="all, delete-orphan"
    )


class ResearchReport(Base):
    __tablename__ = "research_report"
    __table_args__ = (
        CheckConstraint("is_ai_product = 1", name="ck_research_report_ai_product"),
        Index("idx_research_report_task", "research_task_id"),
    )

    id: Mapped[int] = pk_column()
    research_task_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("research_task.id", ondelete="CASCADE"), nullable=False, unique=True, comment="关联研究任务；TODO(待确认)"
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="报告标题；TODO(待确认)"
    )
    summary: Mapped[str] = mapped_column(
        LongText, nullable=False, comment="报告摘要；TODO(待确认)"
    )
    content: Mapped[str] = mapped_column(
        LongText, nullable=False, comment="报告正文；TODO(待确认)"
    )
    sections: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="章节、章节结论和排序；TODO(待确认)"
    )
    conclusions: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="结构化结论集合；TODO(待确认)"
    )
    generation_trace: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="输入快照、提示词/模型版本和生成时间；TODO(待确认)"
    )
    raw_ai_response: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="AI 原始响应；复用一期语义；TODO(待确认)"
    )
    is_ai_product: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1", comment="是否 AI 产物；研究报告必须 true"
    )
    status: Mapped[ResearchReportStatus] = mapped_column(
        enum_type(ResearchReportStatus, "research_report_status"),
        nullable=False,
        default=ResearchReportStatus.success,
        comment="success/failed/discarded；TODO(待确认)：报告状态枚举",
    )
    source_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="关联引用数量；TODO(待确认)"
    )
    created_at: Mapped[datetime] = _phase2_created_at_column()
    updated_at: Mapped[datetime] = _updated_at_column()

    research_task: Mapped["ResearchTask"] = relationship("ResearchTask", back_populates="report")
    references: Mapped[list["ResearchReference"]] = relationship(
        "ResearchReference", back_populates="report", cascade="all, delete-orphan"
    )


class ResearchReference(Base):
    __tablename__ = "research_reference"
    __table_args__ = (Index("idx_research_reference_report", "report_id"),)

    id: Mapped[int] = pk_column()
    report_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("research_report.id", ondelete="CASCADE"), nullable=False, comment="关联研究报告；TODO(待确认)"
    )
    source_kind: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="external_url/collection_result/material；TODO(待确认)：枚举"
    )
    source_url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="外部来源 URL；TODO(待确认)"
    )
    source_title: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="来源标题；TODO(待确认)"
    )
    search_provider: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="检索源/供应商；TODO(待确认)，不代表锁定供应商"
    )
    collection_result_id: Mapped[int | None] = mapped_column(
        BigInt, ForeignKey("collection_result.id"), nullable=True, comment="第二步采集结果；TODO(待确认)"
    )
    material_id: Mapped[int | None] = mapped_column(
        BigInt, ForeignKey("material.id"), nullable=True, comment="一期资料条目；TODO(待确认)"
    )
    source_snapshot: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="引用时标题/摘要/原文快照；TODO(待确认)：json/text 存储方式"
    )
    page_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="页码；引用增强字段；TODO(待确认)"
    )
    paragraph_locator: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="段落/章节定位；引用增强字段；TODO(待确认)"
    )
    evidence_summary: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="证据摘要；引用增强字段；TODO(待确认)"
    )
    source_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="检索源类型；引用增强字段；TODO(待确认)"
    )
    cited_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, comment="建立引用时间；TODO(待确认)"
    )
    created_at: Mapped[datetime] = _phase2_created_at_column()

    report: Mapped["ResearchReport"] = relationship("ResearchReport", back_populates="references")
