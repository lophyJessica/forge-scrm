"""ORM 基类与跨方言类型别名。

DDL 以 MySQL 为标准；SQLite 用 variant 兼容，保证同一套 models 两边都能建表。
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


# bigint 主键/外键：SQLite 需要 INTEGER 才能自增
BigInt = BigInteger().with_variant(Integer, "sqlite")

# longtext：MySQL 用 LONGTEXT，SQLite 用 TEXT
LongText = Text().with_variant(mysql.LONGTEXT, "mysql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def pk_column():
    return mapped_column(BigInt, primary_key=True, autoincrement=True, comment="主键")


def created_at_column():
    return mapped_column(
        DateTime, nullable=False, default=utcnow, comment="创建时间"
    )
