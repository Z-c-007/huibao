"""路由聚合器：所有 API 路由子模块统一在这里挂载，外层 main.py 只 include 它。"""
from fastapi import APIRouter

from .routes import health, chat, map, pra, regulatory, reports

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(map.router)
api_router.include_router(pra.router)
api_router.include_router(regulatory.router)
api_router.include_router(reports.router)

