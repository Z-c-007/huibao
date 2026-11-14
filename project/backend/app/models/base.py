"""ORM 模型的公共基类，集中保存数据库表的元数据。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
