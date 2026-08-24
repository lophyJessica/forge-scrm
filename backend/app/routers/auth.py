"""认证路由（模块 05）：登录 / 登出 / 当前用户 / 修改自己的密码。"""

from fastapi import APIRouter

from app.core.config import settings
from app.core.database import get_db  # noqa: F401
from app.core.deps import CurrentUser, DbSession
from app.core.enums import UserStatus
from app.core.exceptions import BizError, unauthorized
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.base import utcnow
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    UserOut,
)
from app.schemas.common import OkResult
from sqlalchemy import select

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse, summary="账号密码登录（D7，一期仅此方式）")
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        # 记录失败但不落任何明文密码（S05）
        logger.warning("登录失败：username=%s", payload.username)
        raise unauthorized("账号或密码错误")
    if user.status == UserStatus.停用:
        raise BizError("账号已停用，无法登录", 403)

    token, expires_in = create_access_token(user.id, user.username, user.role.value)
    user.last_login_at = utcnow()
    db.commit()
    db.refresh(user)

    must_change = verify_password(settings.seed_admin_password, user.password_hash)
    logger.info("登录成功：user_id=%s role=%s", user.id, user.role.value)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
        must_change_password=must_change,
    )


@router.post("/logout", response_model=OkResult, summary="登出（客户端丢弃 token，一期无服务端黑名单）")
def logout(current_user: CurrentUser) -> OkResult:
    logger.info("登出：user_id=%s", current_user.id)
    return OkResult(message="已登出")


@router.get("/me", response_model=UserOut, summary="当前登录用户")
def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/change-password", response_model=OkResult, summary="修改自己的密码")
def change_password(
    payload: PasswordChangeRequest, current_user: CurrentUser, db: DbSession
) -> OkResult:
    if not verify_password(payload.old_password, current_user.password_hash):
        raise BizError("原密码不正确")
    if payload.old_password == payload.new_password:
        raise BizError("新密码不能与原密码相同")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    logger.info("密码已修改：user_id=%s", current_user.id)
    return OkResult(message="密码已修改，请使用新密码重新登录")
