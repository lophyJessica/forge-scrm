"""业务方向 / 专业方向字典表（选题库字段清单 §一、§二）。"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, created_at_column, pk_column


class DirectionStatus(StrEnum):
    """方向记录状态：一期只做新增，inactive 预留。"""

    active = "active"
    inactive = "inactive"


class BusinessDirection(Base):
    __tablename__ = "business_direction"

    id: Mapped[int] = pk_column()
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="业务方向名称，唯一")
    status: Mapped[DirectionStatus] = mapped_column(
        enum_type(DirectionStatus, "direction_status"),
        nullable=False,
        default=DirectionStatus.active,
        comment="active / inactive（一期只做新增）",
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人"
    )
    created_at: Mapped[datetime] = created_at_column()

    specialties: Mapped[list["Specialty"]] = relationship(
        "Specialty", back_populates="business_direction", lazy="selectin"
    )


class Specialty(Base):
    """专业方向（挂业务方向下）；表名 specialty，与 topic 枚举 Specialty 无关。"""

    __tablename__ = "specialty"
    __table_args__ = (
        UniqueConstraint("business_direction_id", "name", name="uk_specialty_direction_name"),
    )

    id: Mapped[int] = pk_column()
    business_direction_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("business_direction.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属业务方向 id",
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="专业方向名称，同业务方向下唯一"
    )
    status: Mapped[DirectionStatus] = mapped_column(
        enum_type(DirectionStatus, "direction_status"),
        nullable=False,
        default=DirectionStatus.active,
        comment="active / inactive",
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人"
    )
    created_at: Mapped[datetime] = created_at_column()

    business_direction: Mapped["BusinessDirection"] = relationship(
        "BusinessDirection", back_populates="specialties"
    )
