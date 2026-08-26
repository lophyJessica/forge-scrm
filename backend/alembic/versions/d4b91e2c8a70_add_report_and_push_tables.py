"""add report and push skeleton tables

Revision ID: d4b91e2c8a70
Revises: 8f5d2a1c7b90
Create Date: 2026-08-26

幂等：表已存在则跳过创建。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.engine.reflection import Inspector

revision: str = "d4b91e2c8a70"
down_revision: Union[str, None] = "8f5d2a1c7b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(Inspector.from_engine(bind).get_table_names())


def upgrade() -> None:
    existing = _tables()
    bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    longtext = sa.Text().with_variant(mysql.LONGTEXT(), "mysql")

    if "report" not in existing:
        op.create_table(
            "report",
            sa.Column("id", bigint, autoincrement=True, nullable=False, comment="主键"),
            sa.Column("report_no", sa.String(length=64), nullable=False, comment="报告编号；新增建议，待确认"),
            sa.Column(
                "report_type",
                sa.Enum("运营数据报告", "市场分析周报", name="report_type"),
                nullable=False,
                comment="运营数据报告/市场分析周报；枚举新增建议，待确认",
            ),
            sa.Column("title", sa.String(length=500), nullable=False, comment="报告标题"),
            sa.Column("period_start", sa.DateTime(), nullable=False, comment="报告周期开始"),
            sa.Column("period_end", sa.DateTime(), nullable=False, comment="报告周期结束"),
            sa.Column("template_id", bigint, nullable=True, comment="使用的报告模板；本期模板实体未展开"),
            sa.Column("source_config", sa.JSON(), nullable=False, comment="来源实体、时间窗和口径配置"),
            sa.Column("source_snapshot", sa.JSON(), nullable=True, comment="生成时来源摘要/快照"),
            sa.Column("summary", longtext, nullable=False, comment="报告摘要"),
            sa.Column("content", longtext, nullable=False, comment="报告正文"),
            sa.Column("sections", sa.JSON(), nullable=True, comment="章节、数据表和结论结构"),
            sa.Column("conclusions", sa.JSON(), nullable=True, comment="结构化结论与建议"),
            sa.Column("generation_trace", sa.JSON(), nullable=True, comment="生成输入、快照、时间和版本"),
            sa.Column("raw_ai_response", longtext, nullable=True, comment="AI 原始响应"),
            sa.Column("is_ai_product", sa.Boolean(), server_default="1", nullable=False, comment="AI 产物标记；对齐 R8"),
            sa.Column(
                "generation_status",
                sa.Enum("待生成", "生成中", "已完成", "失败", name="report_generation_status"),
                nullable=False,
                comment="待生成/生成中/已完成/失败",
            ),
            sa.Column(
                "review_status",
                sa.Enum("默认通过", "抽查中", "已确认", "待审核", "已废弃", name="report_review_status"),
                nullable=False,
                comment="默认通过/抽查中/已确认/待审核/已废弃",
            ),
            sa.Column("retry_count", sa.Integer(), nullable=False, comment="生成重试次数"),
            sa.Column("error_code", sa.String(length=64), nullable=True, comment="生成失败错误码"),
            sa.Column("error_message", longtext, nullable=True, comment="生成失败说明"),
            sa.Column("created_by", bigint, nullable=False, comment="创建人"),
            sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, comment="修改时间"),
            sa.Column("generated_at", sa.DateTime(), nullable=True, comment="报告生成完成时间"),
            sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("report_no"),
        )
        with op.batch_alter_table("report", schema=None) as batch_op:
            batch_op.create_index("idx_report_type_status", ["report_type", "generation_status"], unique=False)
            batch_op.create_index("idx_report_created_at", ["created_at"], unique=False)
            batch_op.create_index("idx_report_period", ["period_start", "period_end"], unique=False)

    existing = _tables()
    if "report_push_task" not in existing:
        op.create_table(
            "report_push_task",
            sa.Column("id", bigint, autoincrement=True, nullable=False, comment="主键"),
            sa.Column("task_no", sa.String(length=64), nullable=False, comment="推送任务编号"),
            sa.Column("report_id", bigint, nullable=False, comment="关联已完成报告"),
            sa.Column(
                "channel",
                sa.Enum("飞书", "微信", name="report_push_channel"),
                nullable=False,
                comment="飞书/微信；API 待实测",
            ),
            sa.Column(
                "recipient_type",
                sa.Enum("指定人", "群", name="report_push_recipient_type"),
                nullable=False,
                comment="指定人/群",
            ),
            sa.Column("target_object", sa.String(length=255), nullable=False, comment="目标人或群标识"),
            sa.Column("message_config", sa.JSON(), nullable=True, comment="摘要/正文/链接/卡片配置"),
            sa.Column("authorization_snapshot", sa.JSON(), nullable=True, comment="授权校验结果，不保存凭据"),
            sa.Column(
                "status",
                sa.Enum("待推送", "推送中", "已推送", "失败", name="report_push_status"),
                nullable=False,
                comment="待推送/推送中/已推送/失败",
            ),
            sa.Column("retry_count", sa.Integer(), nullable=False, comment="任务重试次数"),
            sa.Column("created_by", bigint, nullable=False, comment="创建人"),
            sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, comment="修改时间"),
            sa.ForeignKeyConstraint(["report_id"], ["report.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("task_no"),
        )
        with op.batch_alter_table("report_push_task", schema=None) as batch_op:
            batch_op.create_index("idx_report_push_task_report", ["report_id"], unique=False)
            batch_op.create_index("idx_report_push_task_status", ["status"], unique=False)

    existing = _tables()
    if "report_push_record" not in existing:
        op.create_table(
            "report_push_record",
            sa.Column("id", bigint, autoincrement=True, nullable=False, comment="主键"),
            sa.Column("push_task_id", bigint, nullable=False, comment="关联推送任务"),
            sa.Column(
                "channel",
                sa.Enum("飞书", "微信", name="report_push_record_channel"),
                nullable=False,
                comment="目标渠道：飞书/微信",
            ),
            sa.Column("target_object", sa.String(length=255), nullable=False, comment="实际目标人或群标识"),
            sa.Column(
                "recipient_type",
                sa.Enum("指定人", "群", name="report_push_record_recipient_type"),
                nullable=False,
                comment="人/群",
            ),
            sa.Column("message_summary", longtext, nullable=False, comment="实际发送的消息摘要"),
            sa.Column("sent_at", sa.DateTime(), nullable=True, comment="实际发送时间"),
            sa.Column(
                "status",
                sa.Enum("待推送", "推送中", "已推送", "失败", name="report_push_record_status"),
                nullable=False,
                comment="待推送/推送中/已推送/失败",
            ),
            sa.Column("provider_message_id", sa.String(length=255), nullable=True, comment="渠道返回消息 ID"),
            sa.Column("error_code", sa.String(length=64), nullable=True, comment="失败时的渠道错误码"),
            sa.Column("error_message", longtext, nullable=True, comment="失败时错误说明"),
            sa.Column("response_snapshot", sa.JSON(), nullable=True, comment="渠道响应摘要，不保存敏感凭据"),
            sa.Column("attempt_no", sa.Integer(), nullable=False, comment="发送尝试序号"),
            sa.Column("created_at", sa.DateTime(), nullable=False, comment="记录创建时间"),
            sa.ForeignKeyConstraint(["push_task_id"], ["report_push_task.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("report_push_record", schema=None) as batch_op:
            batch_op.create_index("idx_report_push_record_task", ["push_task_id"], unique=False)


def downgrade() -> None:
    existing = _tables()
    if "report_push_record" in existing:
        with op.batch_alter_table("report_push_record", schema=None) as batch_op:
            batch_op.drop_index("idx_report_push_record_task")
        op.drop_table("report_push_record")
    if "report_push_task" in existing:
        with op.batch_alter_table("report_push_task", schema=None) as batch_op:
            batch_op.drop_index("idx_report_push_task_status")
            batch_op.drop_index("idx_report_push_task_report")
        op.drop_table("report_push_task")
    if "report" in existing:
        with op.batch_alter_table("report", schema=None) as batch_op:
            batch_op.drop_index("idx_report_period")
            batch_op.drop_index("idx_report_created_at")
            batch_op.drop_index("idx_report_type_status")
        op.drop_table("report")
