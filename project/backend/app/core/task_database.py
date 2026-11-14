from collections.abc import AsyncIterator

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import (
    PG_HOST,
    PG_PORT,
    TASK_PG_DB,
    TASK_PG_PASSWORD,
    TASK_PG_USER,
)


# 1. 构造数据库连接地址
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=TASK_PG_USER,
    password=TASK_PG_PASSWORD,
    host=PG_HOST,
    port=PG_PORT,
    database=TASK_PG_DB,
)


# 2. 创建数据库 Engine
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# 3. 创建 Session 工厂
SessionFactory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


# 4. 为请求提供 Session
async def get_task_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session