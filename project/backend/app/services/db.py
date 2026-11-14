"""数据库层：建库用写权限，查询一律只读。"""
import psycopg
from ..core.config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, DEMO_WATER_UNITS
from .demo_data import install_demo_inventory

def get_db(*, include_demo=True):
    """业务查询一律走只读连接（最小权限：只读由数据库角色 ai_reader 保证，不再靠连接参数）"""
    conn = psycopg.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,        # 注意：psycopg 的关键字是 dbname，不是 database
        user=PG_USER,
        password=PG_PASSWORD,
        autocommit=True,
    )
    try:
        if DEMO_WATER_UNITS and include_demo:
            install_demo_inventory(conn)
        return conn
    except BaseException:
        conn.close()
        raise
