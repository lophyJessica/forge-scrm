"""资料库相关表：material_class / material / tag / material_tag
（context/05 §4.1-§4.2 / 核心字段清单 §1）。
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MaterialStatus, SourceType, TrustLevel
from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, LongText, created_at_column, pk_column


class MaterialClass(Base):
    __tablename__ = "material_class"

    id: Mapped[int] = pk_column()
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="分类名（唯一）"
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInt, ForeignKey("material_class.id"), nullable=True, comment="父级分类，可选层级"
    )
    sort: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0, comment="⚠️ 新增建议字段：排序"
    )
    created_at: Mapped[datetime] = created_at_column()


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = pk_column()
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="标签名（唯一）"
    )
    group_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="可选标签组；一期不强制分组，可为空（D1）"
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=True, comment="⚠️ 技术映射：创建人"
    )
    created_at: Mapped[datetime] = created_at_column()


class MaterialTag(Base):
    __tablename__ = "material_tag"
    __table_args__ = (
        UniqueConstraint("material_id", "tag_id", name="uk_material_tag"),
    )

    id: Mapped[int] = pk_column()
    material_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("material.id", ondelete="CASCADE"), nullable=False, comment="资料 id"
    )
    tag_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("tag.id", ondelete="CASCADE"), nullable=False, comment="标签 id"
    )

    tag: Mapped["Tag"] = relationship("Tag", lazy="joined")


class Material(Base):
    __tablename__ = "material"
    __table_args__ = (
        Index("idx_material_class_id", "class_id"),
        Index("idx_material_status", "status"),
        Index("idx_material_valid_until", "valid_until"),
        Index("idx_material_title", "title"),
    )

    id: Mapped[int] = pk_column()
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="资料标题")
    content: Mapped[str] = mapped_column(LongText, nullable=False, comment="资料正文")
    class_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("material_class.id"), nullable=False, comment="所属分类"
    )
    source_type: Mapped[SourceType] = mapped_column(
        enum_type(SourceType, "material_source_type"),
        nullable=False,
        comment="公众号/报告/社交/客户/思考/对标",
    )
    source_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="来源链接"
    )
    trust_level: Mapped[TrustLevel] = mapped_column(
        enum_type(TrustLevel, "material_trust_level"), nullable=False, comment="高/中/低"
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, comment="有效期起")
    valid_until: Mapped[date] = mapped_column(Date, nullable=False, comment="有效期止")
    status: Mapped[MaterialStatus] = mapped_column(
        enum_type(MaterialStatus, "material_status"),
        nullable=False,
        default=MaterialStatus.草稿,
        comment="草稿/待审核/已生效/已停用/已过期/已废弃",
    )
    is_ai_product: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否 AI 产物"
    )
    source_analysis_task_id: Mapped[int | None] = mapped_column(
        BigInt,
        ForeignKey("analysis_task.id"),
        nullable=True,
        comment="AI 回写资料关联的来源分析任务",
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

    material_class: Mapped["MaterialClass"] = relationship("MaterialClass", lazy="joined")
    tag_links: Mapped[list["MaterialTag"]] = relationship(
        "MaterialTag", lazy="selectin", cascade="all, delete-orphan"
    )
