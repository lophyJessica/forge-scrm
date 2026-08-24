"""用户表（context/05 §4.8 / 核心字段清单 §5）。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import UserRole, UserStatus
from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, created_at_column, pk_column


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = pk_column()
    username: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True, comment="唯一登录账号（D7）"
    )
    password_hash: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="密码哈希，不保存明文（D7）"
    )
    role: Mapped[UserRole] = mapped_column(
        enum_type(UserRole, "user_role"), nullable=False, comment="管理员/成员"
    )
    status: Mapped[UserStatus] = mapped_column(
        enum_type(UserStatus, "user_status"),
        nullable=False,
        default=UserStatus.启用,
        comment="启用/停用",
    )
    functional_permissions: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="管理员分配的功能权限集合"
    )
    data_scope: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="数据权限范围（全量/指定资料分类/指定数据源）"
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInt, nullable=True, comment="创建人（种子管理员为空）"
    )
    created_at: Mapped[datetime] = created_at_column()
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="⚠️ 新增建议字段：最后登录时间"
    )
