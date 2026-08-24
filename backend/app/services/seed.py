"""种子数据：管理员账号 + 资料分类枚举（context/05 §2）。

首次启动自动执行，幂等。默认密码来自环境变量 SEED_ADMIN_PASSWORD，登录后提示改密。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import DataScopeType, MaterialClassName, UserRole, UserStatus
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.material import MaterialClass
from app.models.user import User

logger = get_logger(__name__)


def seed_admin(db: Session) -> None:
    exists = db.scalar(select(User).where(User.username == settings.seed_admin_username))
    if exists:
        return
    admin = User(
        username=settings.seed_admin_username,
        password_hash=hash_password(settings.seed_admin_password),
        role=UserRole.管理员,
        status=UserStatus.启用,
        functional_permissions=[],
        data_scope={"type": DataScopeType.全量.value},
        created_by=None,
    )
    db.add(admin)
    db.commit()
    logger.info("已创建种子管理员账号：%s（请首次登录后立即修改密码）", admin.username)


def seed_material_classes(db: Session) -> None:
    for idx, name in enumerate(MaterialClassName):
        if db.scalar(select(MaterialClass).where(MaterialClass.name == name.value)):
            continue
        db.add(MaterialClass(name=name.value, parent_id=None, sort=idx))
    db.commit()


def run_seed(db: Session) -> None:
    seed_admin(db)
    seed_material_classes(db)
