"""全局配置：统一从 .env 读取，路径一律以项目根为基准，不依赖当前工作目录。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录：backend/（本文件位于 backend/app/core/config.py）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 显式指定 .env 路径，保证从任何目录启动都能读到
load_dotenv(BASE_DIR / ".env")


def _path(key: str, default: str) -> Path:
    return BASE_DIR / os.environ.get(key, default)


# ===== LLM =====
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# ===== 数据 =====
DB_PATH = _path("DB_PATH", "data/water.db")
AUDIT_PATH = _path("AUDIT_PATH", "data/audit.jsonl")

# ===== PostgreSQL（W8 起的空间数据库；Day 11 起 db.py 消费） =====
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_DB = os.environ.get("PG_DB", "ai_water_budget")
PG_USER = os.environ.get("PG_USER", "ai_reader")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "")
# Explicit opt-in via .env: demo rows exist only inside each query connection.
DEMO_WATER_UNITS = os.environ.get("DEMO_WATER_UNITS", "false").lower() in {"true", "1", "yes"}
# ===== 任务学习数据库 =====
TASK_PG_DB = os.environ.get("TASK_PG_DB", "learning_tasks")
TASK_PG_USER = os.environ.get("TASK_PG_USER", "task_app")
TASK_PG_PASSWORD = os.environ["TASK_PG_PASSWORD"]
# ===== CORS =====
CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
]
