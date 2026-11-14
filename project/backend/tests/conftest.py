"""pytest 全局夹具：测试一律连独立测试库（ai_water_budget_test），与开发数据隔离。

关键时序：config.py 在“被导入时”读取环境变量定值，所以必须在任何 app 模块导入之前
改写 os.environ——pytest 先加载 conftest.py 再收集测试模块，顶层代码天然最早执行；
load_dotenv 不覆盖已存在的环境变量，所以这里对 os.environ 的赋值优先级高于 .env 文件。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR / ".env")

# 只换库不换身份：应用在测试中仍以只读角色 ai_reader 连接（最小权限路径不变，
# ai_reader 在测试库的 SELECT 权限由 w9_00 授予）
os.environ["PG_DB"] = os.environ["TEST_PG_DB"]
os.environ["DEMO_WATER_UNITS"] = "false"

import pytest  # noqa: E402  （必须在环境变量改写之后再 import 任何 app 模块）

from psycopg import connect  # noqa: E402


def _reset_seed():
    """用测试专用可写角色重置种子，并校验空间基础数据在位。"""
    conn = connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ["PG_PORT"]),
        dbname=os.environ["TEST_PG_DB"],
        user=os.environ["TEST_PG_USER"],
        password=os.environ["TEST_PG_PASSWORD"],
        autocommit=True,
    )
    try:
        counts = conn.execute(
            "SELECT (SELECT COUNT(*) FROM districts), (SELECT COUNT(*) FROM streets), "
            "(SELECT COUNT(*) FROM rivers)"
        ).fetchone()
        if tuple(counts) != (4, 8, 868):
            raise RuntimeError(
                f"测试库基础数据缺失（districts/streets/rivers = {tuple(counts)}），"
                "请先执行 sql/w9_00_test_db.sql"
            )
        conn.execute("TRUNCATE water_users")
        conn.execute(
            "INSERT INTO water_users (name, industry, water_used, budget, geom) VALUES "
            "('通州某制造企业', '制造业', 12000, 10000, ST_SetSRID(ST_MakePoint(116.72, 39.80), 4326)), "
            "('大兴某制造企业', '制造业', 15000, 20000, ST_SetSRID(ST_MakePoint(116.35, 39.60), 4326)), "
            "('朝阳某酒店', '服务业', 3000, 4000, ST_SetSRID(ST_MakePoint(116.50, 39.90), 4326)), "
            "('顺义某农场', '农业', 800, 1200, ST_SetSRID(ST_MakePoint(116.78, 40.12), 4326))"
        )
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def reset_seed():
    """每条用例前重置种子：可重复、互不污染（企业实践：测试数据夹具）"""
    _reset_seed()
    yield
