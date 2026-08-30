"""add report template management

Revision ID: b6c1e2d3f4a5
Revises: b6d4e8f1a2c3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.engine.reflection import Inspector


revision: str = "b6c1e2d3f4a5"
down_revision: Union[str, None] = "b6d4e8f1a2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(Inspector.from_engine(op.get_bind()).get_table_names())


def upgrade() -> None:
    bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    longtext = sa.Text().with_variant(mysql.LONGTEXT(), "mysql")
    if "report_template" not in _tables():
        op.create_table(
            "report_template",
            sa.Column("id", bigint, autoincrement=True, nullable=False, comment="主键"),
            sa.Column(
                "report_type",
                sa.Enum("运营数据报告", "市场分析周报", name="report_template_type"),
                nullable=False,
                comment="模板适用的报告类型",
            ),
            sa.Column("name", sa.String(length=100), nullable=False, comment="模板名称"),
            sa.Column("content_schema", sa.JSON(), nullable=False, comment="模板内容结构"),
            sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False, comment="是否默认模板"),
            sa.Column(
                "status",
                sa.Enum("启用", "停用", name="report_template_status"),
                nullable=False,
                comment="启用/停用",
            ),
            sa.Column("created_by", bigint, nullable=False, comment="创建人"),
            sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, comment="修改时间"),
            sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("report_template", schema=None) as batch_op:
            batch_op.create_index("idx_report_template_type_status", ["report_type", "status"], unique=False)
            batch_op.create_index("idx_report_template_default", ["report_type", "is_default"], unique=False)

    if "report" in _tables():
        foreign_keys = Inspector.from_engine(op.get_bind()).get_foreign_keys("report")
        if not any("template_id" in (key.get("constrained_columns") or []) for key in foreign_keys):
            with op.batch_alter_table("report", schema=None) as batch_op:
                batch_op.create_foreign_key("fk_report_template_id", "report_template", ["template_id"], ["id"])


def downgrade() -> None:
    if "report" in _tables():
        with op.batch_alter_table("report", schema=None) as batch_op:
            batch_op.drop_constraint("fk_report_template_id", type_="foreignkey")
    if "report_template" in _tables():
        with op.batch_alter_table("report_template", schema=None) as batch_op:
            batch_op.drop_index("idx_report_template_default")
            batch_op.drop_index("idx_report_template_type_status")
        op.drop_table("report_template")
