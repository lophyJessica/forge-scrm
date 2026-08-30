"""allow analysis tasks to use collection results as inputs

Revision ID: b6d4e8f1a2c3
Revises: a7c3e5f90b21
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b6d4e8f1a2c3"
down_revision: str | None = "a7c3e5f90b21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    with op.batch_alter_table("collection_result") as batch_op:
        batch_op.create_unique_constraint("uk_collection_result_record", ["record_id"])
        batch_op.create_unique_constraint(
            "uk_collection_result_task_account", ["task_id", "benchmark_account_id"]
        )
    with op.batch_alter_table("analysis_task_input") as batch_op:
        batch_op.alter_column("raw_data_id", existing_type=bigint, nullable=True)
        batch_op.add_column(sa.Column("collection_result_id", bigint, nullable=True))
        batch_op.create_foreign_key(
            "fk_analysis_task_input_collection_result",
            "collection_result",
            ["collection_result_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uk_analysis_task_collection_input", ["task_id", "collection_result_id"]
        )


def downgrade() -> None:
    bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    with op.batch_alter_table("analysis_task_input") as batch_op:
        batch_op.drop_constraint("uk_analysis_task_collection_input", type_="unique")
        batch_op.drop_constraint("fk_analysis_task_input_collection_result", type_="foreignkey")
        batch_op.drop_column("collection_result_id")
        batch_op.alter_column("raw_data_id", existing_type=bigint, nullable=False)
    with op.batch_alter_table("collection_result") as batch_op:
        batch_op.drop_constraint("uk_collection_result_task_account", type_="unique")
        batch_op.drop_constraint("uk_collection_result_record", type_="unique")
