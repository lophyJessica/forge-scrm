"""seed default generation prompt templates

Revision ID: 8f5d2a1c7b90
Revises: c7293fe1b190
Create Date: 2026-08-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.enums import PromptStatus, PromptTaskType
from app.services.script_service import DEFAULT_SYSTEM_PROMPT as DEFAULT_SCRIPT_SYSTEM_PROMPT
from app.services.topic_service import DEFAULT_SYSTEM_PROMPT as DEFAULT_TOPIC_SYSTEM_PROMPT

revision: str = "8f5d2a1c7b90"
down_revision: Union[str, None] = "c7293fe1b190"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    prompt_template = sa.Table("prompt_template", metadata, autoload_with=bind)
    user = sa.Table("user", metadata, autoload_with=bind)
    created_by = bind.execute(sa.select(user.c.id).order_by(user.c.id.asc()).limit(1)).scalar()
    if created_by is None:
        # App startup creates the seed admin after migrations. Runtime fallback keeps
        # an empty database usable until the migration can be rerun with a user row.
        return

    seeds = (
        (PromptTaskType.选题生成.value, "内置选题提示词", DEFAULT_TOPIC_SYSTEM_PROMPT),
        (PromptTaskType.脚本生成.value, "内置脚本提示词", DEFAULT_SCRIPT_SYSTEM_PROMPT),
    )
    for task_type, name, content in seeds:
        exists = bind.execute(
            sa.select(prompt_template.c.id).where(
                prompt_template.c.task_type == task_type,
                prompt_template.c.name == name,
            )
        ).first()
        if exists:
            continue
        bind.execute(
            prompt_template.insert().values(
                task_type=task_type,
                name=name,
                content=content,
                version=1,
                material_combo=None,
                output_schema=None,
                status=PromptStatus.启用.value,
                created_by=created_by,
                created_at=sa.func.now(),
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    prompt_template = sa.Table("prompt_template", metadata, autoload_with=bind)
    bind.execute(
        prompt_template.delete().where(
            sa.or_(
                sa.and_(
                    prompt_template.c.task_type == PromptTaskType.选题生成.value,
                    prompt_template.c.name == "内置选题提示词",
                ),
                sa.and_(
                    prompt_template.c.task_type == PromptTaskType.脚本生成.value,
                    prompt_template.c.name == "内置脚本提示词",
                ),
            )
        )
    )
