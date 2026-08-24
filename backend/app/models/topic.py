"""选题相关表：topic / topic_material（context/05 §4.4 / 核心字段清单 §3）。

D8：一期不建 topic_version 表，人工修改直接更新当前内容。
"""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ScreeningResult, Specialty, TopicStatus
from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, LongText, created_at_column, pk_column


class Topic(Base):
    __tablename__ = "topic"
    __table_args__ = (
        Index("idx_topic_status", "status"),
        Index("idx_topic_direction", "direction"),
        Index("idx_topic_batch_no", "batch_no"),
    )

    id: Mapped[int] = pk_column()
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="选题标题")
    direction: Mapped[str] = mapped_column(String(50), nullable=False, comment="方向/分类")
    specialty: Mapped[Specialty] = mapped_column(
        enum_type(Specialty, "topic_specialty"), nullable=False, comment="专业方向"
    )
    customer_scenario: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="结合场景"
    )
    user_perspective: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="用户视角"
    )
    business_direction: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="经营方向"
    )
    core_angle: Mapped[str] = mapped_column(String(500), nullable=False, comment="核心角度")
    topic_principle: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="选题原则"
    )
    topic_angle: Mapped[str] = mapped_column(String(200), nullable=False, comment="选题角度")
    status: Mapped[TopicStatus] = mapped_column(
        enum_type(TopicStatus, "topic_status"),
        nullable=False,
        default=TopicStatus.待筛选,
        comment="待筛选/已选定/已生成脚本/已使用/已废弃",
    )
    batch_no: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="生成批次号"
    )
    prompt_version_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="可选提示词版本追溯；仅 AI 批量生成路径写入"
    )
    ai_raw_response: Mapped[str | None] = mapped_column(
        LongText,
        nullable=True,
        comment="AI 批量生成时留档；独立/手动创建可为空",
    )
    screening_result: Mapped[ScreeningResult | None] = mapped_column(
        enum_type(ScreeningResult, "topic_screening_result"),
        nullable=True,
        comment="选中/淘汰；完成筛选后必填",
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人"
    )
    created_at: Mapped[datetime] = created_at_column()

    material_links: Mapped[list["TopicMaterial"]] = relationship(
        "TopicMaterial", lazy="selectin", cascade="all, delete-orphan"
    )


class TopicMaterial(Base):
    """可选追溯表；不记录资料引用时不阻塞选题生成、筛选或脚本生成。"""

    __tablename__ = "topic_material"
    __table_args__ = (UniqueConstraint("topic_id", "material_id", name="uk_topic_material"),)

    id: Mapped[int] = pk_column()
    topic_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("topic.id", ondelete="CASCADE"), nullable=False, comment="选题 id"
    )
    material_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("material.id"), nullable=False, comment="引用资料 id"
    )
