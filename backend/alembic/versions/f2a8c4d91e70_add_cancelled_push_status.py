"""add cancelled push status

Revision ID: f2a8c4d91e70
Revises: d4b91e2c8a70
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a8c4d91e70"
down_revision: str | None = "d4b91e2c8a70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_TASK_STATUS = sa.Enum("待推送", "推送中", "已推送", "失败", name="report_push_status")
NEW_TASK_STATUS = sa.Enum(
    "待推送", "推送中", "已推送", "失败", "已取消", name="report_push_status"
)
OLD_RECORD_STATUS = sa.Enum(
    "待推送", "推送中", "已推送", "失败", name="report_push_record_status"
)
NEW_RECORD_STATUS = sa.Enum(
    "待推送", "推送中", "已推送", "失败", "已取消", name="report_push_record_status"
)


def upgrade() -> None:
    op.alter_column(
        "report_push_task",
        "status",
        existing_type=OLD_TASK_STATUS,
        type_=NEW_TASK_STATUS,
        existing_nullable=False,
        existing_comment="待推送/推送中/已推送/失败",
        comment="待推送/推送中/已推送/失败/已取消",
    )
    op.alter_column(
        "report_push_record",
        "status",
        existing_type=OLD_RECORD_STATUS,
        type_=NEW_RECORD_STATUS,
        existing_nullable=False,
        existing_comment="待推送/推送中/已推送/失败",
        comment="待推送/推送中/已推送/失败/已取消",
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE report_push_task SET status = '待推送' WHERE status = '已取消'")
    )
    op.alter_column(
        "report_push_record",
        "status",
        existing_type=NEW_RECORD_STATUS,
        type_=OLD_RECORD_STATUS,
        existing_nullable=False,
        existing_comment="待推送/推送中/已推送/失败/已取消",
        comment="待推送/推送中/已推送/失败",
    )
    op.alter_column(
        "report_push_task",
        "status",
        existing_type=NEW_TASK_STATUS,
        type_=OLD_TASK_STATUS,
        existing_nullable=False,
        existing_comment="待推送/推送中/已推送/失败/已取消",
        comment="待推送/推送中/已推送/失败",
    )
