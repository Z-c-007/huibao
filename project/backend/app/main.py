from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.main import api_router
from .core.config import CORS_ORIGINS
from .api.routes.pra import register_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 数据库由 DBA 脚本（sql/w8_*、w9_00）供给，启动时不再自建自灌
    yield


app = FastAPI(
    title="水利预算监管助手 API",
    description="W7：把 W6 的 Function Calling 工具编排包装成 FastAPI 服务",
    version="0.1.0",
    lifespan=lifespan,
)
register_middleware(app)

# 放行前端开发服务器（Vite 默认 5173），生产环境按需收紧
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")