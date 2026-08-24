"""提示词模板表 prompt_template（context/05 §4.3 / 核心字段清单 §2）。

注：prompt_version 独立版本表标注为「⚠️ 新增建议，待确认」，一期不建表（沿用 version 字段）。
"""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import PromptStatus, PromptTaskType
from app.models._enum_type import enum_type
from app.models.base import Base, BigInt, created_at_column, pk_column


class PromptTemplate(Base):
    __tablename__ = "prompt_template"

    id: Mapped[int] = pk_column()
    task_type: Mapped[PromptTaskType] = mapped_column(
        enum_type(PromptTaskType, "prompt_task_type"),
        nullable=False,
        comment="选题生成/脚本生成/资料分析/数据分析",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模板名称")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="提示词正文")
    version: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=1, comment="⚠️ 新增建议字段：当前版本号"
    )
    material_combo: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="固定关联资料组合"
    )
    output_schema: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="输出字段定义；分析任务必填"
    )
    status: Mapped[PromptStatus | None] = mapped_column(
        enum_type(PromptStatus, "prompt_status"),
        nullable=True,
        default=PromptStatus.启用,
        comment="⚠️ 新增建议字段：启用/停用",
    )
    created_by: Mapped[int] = mapped_column(
        BigInt, ForeignKey("user.id"), nullable=False, comment="创建人"
    )
    created_at: Mapped[datetime] = created_at_column()
