"""add business_direction and specialty tables

Revision ID: a3f8c2d91e4b
Revises: 1c1a51600ffc
Create Date: 2026-08-25 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3f8c2d91e4b"
down_revision: Union[str, None] = "1c1a51600ffc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_direction",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
            comment="主键",
        ),
        sa.Column("name", sa.String(length=50), nullable=False, comment="业务方向名称，唯一"),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="direction_status"),
            nullable=False,
            comment="active / inactive（一期只做新增）",
        ),
        sa.Column(
            "created_by",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
            comment="创建人",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "specialty",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
            comment="主键",
        ),
        sa.Column(
            "business_direction_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
            comment="所属业务方向 id",
        ),
        sa.Column(
            "name",
            sa.String(length=50),
            nullable=False,
            comment="专业方向名称，同业务方向下唯一",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="direction_status"),
            nullable=False,
            comment="active / inactive",
        ),
        sa.Column(
            "created_by",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
            comment="创建人",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.ForeignKeyConstraint(["business_direction_id"], ["business_direction.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_direction_id", "name", name="uk_specialty_direction_name"),
    )


def downgrade() -> None:
    op.drop_table("specialty")
    op.drop_table("business_direction")
