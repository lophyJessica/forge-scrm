"""脚本相关表：script / script_version（context/05 §4.5 / 核心字段清单 §3）。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ScriptStatus, ScriptStyle
from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, LongText, created_at_column, pk_column, utcnow


class Script(Base):
    __tablename__ = "script"
    __table_args__ = (
        Index("idx_script_topic_id", "topic_id"),
        Index("idx_script_status", "status"),
    )

    id: Mapped[int] = pk_column()
    topic_id: Mapped[int | None] = mapped_column(
        BigInt,
        ForeignKey("topic.id"),
        nullable=True,
        comment="基于选题创建时必填；独立创建时可为空、可后补关联（R10）",
    )
    content: Mapped[str] = mapped_column(LongText, nullable=False, comment="脚本正文")
    style: Mapped[ScriptStyle] = mapped_column(
        enum_type(ScriptStyle, "script_style"),
        nullable=False,
        comment="专业严谨/轻松口语/讲故事",
    )
    content_elements: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="案例/数据/个人观点"
    )
    current_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="当前版本号"
    )
    status: Mapped[ScriptStatus] = mapped_column(
        enum_type(ScriptStatus, "script_status"),
        nullable=False,
        default=ScriptStatus.草稿,
        comment="草稿(派生)/待审核/已通过/已使用(人工标记 D4)/已废弃",
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
    modified_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="最后修改人"
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow, comment="最后修改时间"
    )
    material_refs: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="可选资料追溯"
    )
    prompt_version_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="可选提示词版本追溯"
    )

    versions: Mapped[list["ScriptVersion"]] = relationship(
        "ScriptVersion",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ScriptVersion.version",
    )


class ScriptVersion(Base):
    __tablename__ = "script_version"

    id: Mapped[int] = pk_column()
    script_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("script.id", ondelete="CASCADE"), nullable=False, comment="脚本 id"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, comment="版本号（每改+1）")
    content_snapshot: Mapped[str] = mapped_column(LongText, nullable=False, comment="正文快照")
    changed_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="修改人"
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, comment="修改时间"
    )
    note: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="⚠️ 新增建议字段：修改备注"
    )
