"""跨模型共用的 SQLAlchemy Enum 构造器：统一按枚举「值」落库（中文口径）。"""

from enum import Enum as PyEnum

from sqlalchemy import Enum as SAEnum


def enum_type(enum_cls: type[PyEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda e: [item.value for item in e],
        validate_strings=True,
    )
