"""依赖注入：登录态、角色校验、功能权限校验、数据范围解析。

权限口径严格对齐 context/06-系统边界与角色权限.md §2.2：
- 管理员：全功能；
- 成员：矩阵中标 ✅ 的动作默认可做（受数据范围限制）；
  标「由管理员授权」「待确认」的动作默认无权，须管理员显式授予（矩阵口径：待确认不得默认放权）；
  标 ❌ 的动作成员恒无权。
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import DataScopeType, Permission, UserRole, UserStatus
from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_access_token
from app.models.user import User

DbSession = Annotated[Session, Depends(get_db)]


def _extract_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def get_current_user(request: Request, db: DbSession) -> User:
    token = _extract_token(request)
    if not token:
        raise unauthorized()
    payload = decode_access_token(token)
    if not payload:
        raise unauthorized()
    try:
        user_id = int(payload.get("sub", ""))
    except ValueError:
        raise unauthorized()
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    if user.status == UserStatus.停用:
        raise forbidden("账号已停用")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.管理员:
        raise forbidden("仅管理员可执行该操作")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


def require_member(current_user: CurrentUser) -> User:
    """任意已登录且启用的账号（管理员或成员）。"""
    return current_user


MemberUser = Annotated[User, Depends(require_member)]


def has_permission(user: User, permission: Permission) -> bool:
    if user.role == UserRole.管理员:
        return True
    return permission.value in (user.functional_permissions or [])


def require_permission(permission: Permission):
    """成员需被管理员显式授予该功能权限；管理员恒通过。"""

    def _dep(current_user: CurrentUser) -> User:
        if not has_permission(current_user, permission):
            raise forbidden(f"缺少功能权限：{permission.name}")
        return current_user

    return _dep


# ---------------- 数据范围 ----------------

def allowed_material_class_ids(user: User) -> list[int] | None:
    """返回成员可见的资料分类 id 列表；None 表示全量不受限。"""
    if user.role == UserRole.管理员:
        return None
    scope = user.data_scope or {}
    if scope.get("type", DataScopeType.全量.value) == DataScopeType.全量.value:
        return None
    ids = scope.get("material_class_ids")
    if ids is None:
        return None
    return [int(i) for i in ids]


def allowed_data_source_ids(user: User) -> list[int] | None:
    """返回成员可见的数据源 id 列表；None 表示全量不受限。"""
    if user.role == UserRole.管理员:
        return None
    scope = user.data_scope or {}
    if scope.get("type", DataScopeType.全量.value) == DataScopeType.全量.value:
        return None
    ids = scope.get("data_source_ids")
    if ids is None:
        return None
    return [int(i) for i in ids]


def assert_material_class_visible(user: User, class_id: int) -> None:
    allowed = allowed_material_class_ids(user)
    if allowed is not None and class_id not in allowed:
        raise forbidden("超出数据范围：该资料分类不可见")


def assert_data_source_visible(user: User, source_id: int) -> None:
    allowed = allowed_data_source_ids(user)
    if allowed is not None and source_id not in allowed:
        raise forbidden("超出数据范围：该数据源不可见")
