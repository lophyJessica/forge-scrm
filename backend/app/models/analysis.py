"""数据与分析相关表（context/05 §4.6-§4.7 / 核心字段清单 §4）：

data_source / raw_data / analysis_task / analysis_task_input /
analysis_result / analysis_result_material / analysis_result_topic

D5：data_source 保留自动采集扩展位置（collection_method 预留枚举 + config），一期不实现采集逻辑。
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    AnalysisTaskStatus,
    AnalysisTaskType,
    BusinessObject,
    CollectionMethod,
    DataSourceStatus,
    Platform,
    WritebackMaterialStatus,
    WritebackTopicStatus,
)
from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, LongText, created_at_column, pk_column, utcnow


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[int] = pk_column()
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="名称")
    collection_method: Mapped[CollectionMethod] = mapped_column(
        enum_type(CollectionMethod, "ds_collection_method"),
        nullable=False,
        comment="手动录入/CSV 导入；自动采集枚举仅作架构预留（D5）",
    )
    business_object: Mapped[BusinessObject] = mapped_column(
        enum_type(BusinessObject, "ds_business_object"),
        nullable=False,
        comment="自己账号/对标账号/行业报告/相关热点/评论和私信",
    )
    platform: Mapped[Platform | None] = mapped_column(
        enum_type(Platform, "ds_platform"),
        nullable=True,
        comment="视频号；非平台文本资料可为空",
    )
    account_identifier: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="账号类数据必填"
    )
    is_benchmark: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否对标账号"
    )
    config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="⚠️ 新增建议字段：API/OAuth/调度配置（自动采集架构预留）"
    )
    status: Mapped[DataSourceStatus | None] = mapped_column(
        enum_type(DataSourceStatus, "ds_status"),
        nullable=True,
        default=DataSourceStatus.启用,
        comment="⚠️ 新增建议字段：启用/停用",
    )


class RawData(Base):
    __tablename__ = "raw_data"
    __table_args__ = (Index("idx_raw_data_source_id", "source_id"),)

    id: Mapped[int] = pk_column()
    source_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("data_source.id"), nullable=False, comment="数据源 id"
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, comment="采集时间"
    )
    raw_content: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="原始内容（或本地存储路径）"
    )
    structured: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="结构化字段；一期仅通用基础结构（D6）"
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="采集时间窗开始"
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="采集时间窗结束"
    )
    clean_dedup_record: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="清洗/去重规则或处理记录"
    )

    data_source: Mapped["DataSource"] = relationship("DataSource", lazy="joined")


class AnalysisTask(Base):
    __tablename__ = "analysis_task"
    __table_args__ = (
        Index("idx_analysis_task_status", "status"),
        Index("idx_analysis_task_created_at", "created_at"),
    )

    id: Mapped[int] = pk_column()
    name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="⚠️ 新增建议字段：任务名称"
    )
    type: Mapped[AnalysisTaskType] = mapped_column(
        enum_type(AnalysisTaskType, "analysis_task_type"),
        nullable=False,
        comment="指定分析任务类型",
    )
    prompt_version_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="可选提示词版本快照"
    )
    material_context_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="可选资料库上下文快照"
    )
    output_schema: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="输出字段定义"
    )
    ai_raw_response: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="AI 原始响应留档（执行后写入，含失败响应）"
    )
    status: Mapped[AnalysisTaskStatus] = mapped_column(
        enum_type(AnalysisTaskStatus, "analysis_task_status"),
        nullable=False,
        default=AnalysisTaskStatus.待执行,
        comment="待执行/执行中/已完成/失败/待审核/已确认/已废弃",
    )
    error_message: Mapped[str | None] = mapped_column(
        LongText, nullable=True, comment="失败原因留痕（S03）"
    )
    reviewer_id: Mapped[int | None] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=True, comment="审核人"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="审核时间"
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人"
    )
    created_at: Mapped[datetime] = created_at_column()
    retry_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0, comment="⚠️ 新增建议字段：重试次数"
    )

    inputs: Mapped[list["AnalysisTaskInput"]] = relationship(
        "AnalysisTaskInput", lazy="selectin", cascade="all, delete-orphan"
    )
    results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult", lazy="selectin", cascade="all, delete-orphan"
    )


class AnalysisTaskInput(Base):
    __tablename__ = "analysis_task_input"
    __table_args__ = (
        UniqueConstraint("task_id", "raw_data_id", name="uk_analysis_task_input"),
    )

    id: Mapped[int] = pk_column()
    task_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("analysis_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="分析任务 id",
    )
    raw_data_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("raw_data.id"), nullable=False, comment="原始数据 id"
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    id: Mapped[int] = pk_column()
    task_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("analysis_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="任务 id",
    )
    result_content: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="结构化结果（效果好坏/结论/建议）"
    )
    writeback_material_status: Mapped[WritebackMaterialStatus] = mapped_column(
        enum_type(WritebackMaterialStatus, "result_writeback_material_status"),
        nullable=False,
        default=WritebackMaterialStatus.未回写,
        comment="未回写/已回写（独立动作）",
    )
    writeback_topic_status: Mapped[WritebackTopicStatus] = mapped_column(
        enum_type(WritebackTopicStatus, "result_writeback_topic_status"),
        nullable=False,
        default=WritebackTopicStatus.未反哺,
        comment="未反哺/已反哺（独立动作）",
    )

    material_links: Mapped[list["AnalysisResultMaterial"]] = relationship(
        "AnalysisResultMaterial", lazy="selectin", cascade="all, delete-orphan"
    )
    topic_links: Mapped[list["AnalysisResultTopic"]] = relationship(
        "AnalysisResultTopic", lazy="selectin", cascade="all, delete-orphan"
    )


class AnalysisResultMaterial(Base):
    __tablename__ = "analysis_result_material"

    id: Mapped[int] = pk_column()
    result_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("analysis_result.id", ondelete="CASCADE"),
        nullable=False,
        comment="分析结果 id",
    )
    material_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("material.id"), nullable=False, comment="回写生成的资料 id"
    )


class AnalysisResultTopic(Base):
    __tablename__ = "analysis_result_topic"

    id: Mapped[int] = pk_column()
    result_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("analysis_result.id", ondelete="CASCADE"),
        nullable=False,
        comment="分析结果 id",
    )
    topic_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("topic.id"), nullable=False, comment="反哺生成的选题 id"
    )
