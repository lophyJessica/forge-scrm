"""种子数据：管理员账号 + 资料分类枚举（context/05 §2）。

首次启动自动执行，幂等。默认密码来自环境变量 SEED_ADMIN_PASSWORD，登录后提示改密。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import (
    DataScopeType,
    MaterialClassName,
    PromptStatus,
    PromptTaskType,
    UserRole,
    UserStatus,
)
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.material import MaterialClass
from app.models.prompt import PromptTemplate
from app.models.user import User
from app.services.analysis_service import DEFAULT_SYSTEM_PROMPT as DEFAULT_ANALYSIS_SYSTEM_PROMPT
from app.services.script_service import DEFAULT_SYSTEM_PROMPT as DEFAULT_SCRIPT_SYSTEM_PROMPT
from app.services.topic_service import DEFAULT_SYSTEM_PROMPT as DEFAULT_TOPIC_SYSTEM_PROMPT

logger = get_logger(__name__)

BUILTIN_PROMPTS = {
    PromptTaskType.选题生成: DEFAULT_TOPIC_SYSTEM_PROMPT,
    PromptTaskType.脚本生成: DEFAULT_SCRIPT_SYSTEM_PROMPT,
    PromptTaskType.资料分析: DEFAULT_ANALYSIS_SYSTEM_PROMPT,
    PromptTaskType.数据分析: DEFAULT_ANALYSIS_SYSTEM_PROMPT,
}


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


def seed_builtin_templates(db: Session) -> None:
    admin = db.scalar(select(User).where(User.username == settings.seed_admin_username))
    if admin is None:
        return

    created: list[str] = []
    for task_type in PromptTaskType:
        exists = db.scalar(
            select(PromptTemplate.id).where(
                PromptTemplate.task_type == task_type,
                PromptTemplate.name.like("内置%"),
            )
        )
        if exists:
            continue
        name = f"内置{task_type.value}提示词"
        db.add(
            PromptTemplate(
                task_type=task_type,
                name=name,
                content=BUILTIN_PROMPTS[task_type],
                status=PromptStatus.启用,
                version=1,
                created_by=admin.id,
            )
        )
        created.append(name)
    db.commit()
    if created:
        logger.info("已补建内置提示词模板：%s", "、".join(created))


def run_seed(db: Session) -> None:
    seed_admin(db)
    seed_material_classes(db)
    seed_builtin_templates(db)
