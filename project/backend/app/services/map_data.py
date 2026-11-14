from .db import get_db
from .budget_data import read_water_units, build_inspection
def _feature_collection(conn, table, prop_cols):
    """一张表 → 一个 GeoJSON   FeatureCollection（属性列 + ST_AsGeoJSON 几何）"""
    rows = conn.execute(
        f"SELECT {', '.join(prop_cols)}, ST_AsGeoJSON(geom)::json AS geojson FROM {table}"
    ).fetchall()
    features = [
        {
            "type": "Feature",
            "properties": {col: r[i] for i, col in enumerate(prop_cols)},
            "geometry": r[-1],  # ::json 让 psycopg 直接给 Python dict
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}


def get_base_map():
    """地图首屏三层数据（区县/街道/河道），走 ai_reader 只读"""
    conn = get_db(include_demo=False)
    try:
        return {
            "districts": _feature_collection(conn, "districts", ["name"]),
            "streets": _feature_collection(conn, "streets", ["name"]),
            "rivers": _feature_collection(conn, "rivers", ["name", "ord_stra"]),
        }
    finally:
        conn.close()


def get_water_users(year=2026, quarter=3):
    """Map inventory uses the same statuses/thresholds as the agent inspection."""
    conn = get_db()
    try:
        return build_inspection(read_water_units(conn, year=year, quarter=quarter, require_profiles=True), year=year, quarter=quarter)
    finally:
        conn.close()
