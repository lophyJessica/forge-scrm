"""认证与用户相关 Schema（模块 05）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DataScopeType, UserRole, UserStatus


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)


class DataScope(BaseModel):
    """数据范围：全量 / 指定资料分类 / 指定数据源（context/05 §4.8）。"""

    type: DataScopeType = DataScopeType.全量
    material_class_ids: list[int] | None = None
    data_source_ids: list[int] | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    status: UserStatus
    functional_permissions: list[str] = []
    data_scope: dict = {}
    created_by: int | None = None
    created_at: datetime
    last_login_at: datetime | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    must_change_password: bool = Field(
        False, description="使用默认种子密码登录时为 true，前端提示改密"
    )


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.成员
    functional_permissions: list[str] = []
    data_scope: DataScope = DataScope()


class UserUpdate(BaseModel):
    role: UserRole | None = None
    status: UserStatus | None = None
    functional_permissions: list[str] | None = None
    data_scope: DataScope | None = None


class PasswordResetRequest(BaseModel):
    """管理员重置他人密码。"""

    new_password: str = Field(..., min_length=6, max_length=128)


class PasswordChangeRequest(BaseModel):
    """用户修改自己的密码。"""

    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class PermissionItem(BaseModel):
    code: str
    label: str
