"""narrow push record status

Revision ID: a7c3e5f90b21
Revises: f2a8c4d91e70
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e5f90b21"
down_revision: str | None = "f2a8c4d91e70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUS = sa.Enum(
    "待推送", "推送中", "已推送", "失败", "已取消", name="report_push_record_status"
)
NEW_STATUS = sa.Enum("已推送", "失败", "待推送", name="report_push_record_status")


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE report_push_record SET status = '失败' "
            "WHERE status IN ('推送中', '已取消')"
        )
    )
    op.alter_column(
        "report_push_record",
        "status",
        existing_type=OLD_STATUS,
        type_=NEW_STATUS,
        existing_nullable=False,
        existing_comment="待推送/推送中/已推送/失败/已取消",
        comment="已推送/失败/待推送",
    )


def downgrade() -> None:
    op.alter_column(
        "report_push_record",
        "status",
        existing_type=NEW_STATUS,
        type_=OLD_STATUS,
        existing_nullable=False,
        existing_comment="已推送/失败/待推送",
        comment="待推送/推送中/已推送/失败/已取消",
    )
