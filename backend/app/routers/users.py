"""用户管理路由（模块 05，仅管理员）。"""

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.deps import AdminUser, DbSession
from app.core.enums import ALL_PERMISSIONS, Permission, UserRole, UserStatus
from app.core.exceptions import BizError, not_found
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import (
    PasswordResetRequest,
    PermissionItem,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.schemas.common import OkResult, PageResult

logger = get_logger(__name__)
router = APIRouter(prefix="/api/users", tags=["账号管理"])


@router.get("/permissions", response_model=list[PermissionItem], summary="可分配功能权限字典")
def list_permissions(_: AdminUser) -> list[PermissionItem]:
    return [PermissionItem(code=p.value, label=p.name) for p in Permission]


@router.get("", response_model=PageResult[UserOut], summary="账号列表")
def list_users(
    _: AdminUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
) -> PageResult[UserOut]:
    stmt = select(User)
    if keyword:
        stmt = stmt.where(User.username.like(f"%{keyword}%"))
    if role:
        stmt = stmt.where(User.role == role)
    if status:
        stmt = stmt.where(User.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[UserOut](
        total=total,
        page=page,
        page_size=page_size,
        items=[UserOut.model_validate(r) for r in rows],
    )


@router.post("", response_model=UserOut, summary="创建成员账号（R20：一期不设业务数量上限）")
def create_user(payload: UserCreate, admin: AdminUser, db: DbSession) -> UserOut:
    if db.scalar(select(User).where(User.username == payload.username)):
        raise BizError("登录账号已存在")
    unknown = [p for p in payload.functional_permissions if p not in ALL_PERMISSIONS]
    if unknown:
        raise BizError(f"未知功能权限：{', '.join(unknown)}")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status=UserStatus.启用,
        functional_permissions=payload.functional_permissions,
        data_scope=payload.data_scope.model_dump(mode="json"),
        created_by=admin.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("创建账号：user_id=%s by=%s", user.id, admin.id)
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut, summary="账号详情")
def get_user(user_id: int, _: AdminUser, db: DbSession) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise not_found("账号")
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut, summary="更新角色/功能权限/数据范围")
def update_user(user_id: int, payload: UserUpdate, admin: AdminUser, db: DbSession) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise not_found("账号")
    if payload.functional_permissions is not None:
        unknown = [p for p in payload.functional_permissions if p not in ALL_PERMISSIONS]
        if unknown:
            raise BizError(f"未知功能权限：{', '.join(unknown)}")
        user.functional_permissions = payload.functional_permissions
    if payload.role is not None:
        if user.id == admin.id and payload.role != UserRole.管理员:
            raise BizError("不能取消自己的管理员角色")
        user.role = payload.role
    if payload.status is not None:
        if user.id == admin.id and payload.status == UserStatus.停用:
            raise BizError("不能停用自己的账号")
        user.status = payload.status
    if payload.data_scope is not None:
        user.data_scope = payload.data_scope.model_dump(mode="json")
    db.commit()
    db.refresh(user)
    logger.info("更新账号：user_id=%s by=%s", user.id, admin.id)
    return UserOut.model_validate(user)


@router.post("/{user_id}/disable", response_model=UserOut, summary="停用账号")
def disable_user(user_id: int, admin: AdminUser, db: DbSession) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise not_found("账号")
    if user.id == admin.id:
        raise BizError("不能停用自己的账号")
    user.status = UserStatus.停用
    db.commit()
    db.refresh(user)
    logger.info("停用账号：user_id=%s by=%s", user.id, admin.id)
    return UserOut.model_validate(user)


@router.post("/{user_id}/enable", response_model=UserOut, summary="重新启用账号")
def enable_user(user_id: int, admin: AdminUser, db: DbSession) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise not_found("账号")
    user.status = UserStatus.启用
    db.commit()
    db.refresh(user)
    logger.info("启用账号：user_id=%s by=%s", user.id, admin.id)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=OkResult, summary="重置成员密码")
def reset_password(
    user_id: int, payload: PasswordResetRequest, admin: AdminUser, db: DbSession
) -> OkResult:
    user = db.get(User, user_id)
    if not user:
        raise not_found("账号")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    logger.info("重置密码：user_id=%s by=%s", user.id, admin.id)
    return OkResult(message="密码已重置")
