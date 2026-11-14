"""Optional, connection-local demo inventory; never mutates persistent business tables."""
import json
from pathlib import Path

DEMO_FILE = Path(__file__).resolve().parents[2] / "data" / "demo_water_units.json"


def load_demo_units():
    units = json.loads(DEMO_FILE.read_text(encoding="utf-8"))
    names = set()
    for unit in units:
        if not unit["name"].endswith("（演示）") or unit["name"] in names:
            raise ValueError("演示单位必须标注来源，且名称不能重复")
        names.add(unit["name"])
        if unit["industry"] not in {"制造业", "服务业", "农业", "建筑业"}:
            raise ValueError("演示单位行业不在业务白名单中")
    return units


def install_demo_inventory(conn):
    # A session-local table shadows the unqualified water_users name used by ALL
    # existing tools. The persistent public table and read-only role stay intact.
    # All queries keep real PostGIS filters, deterministic rules, and SQL bindings.
    units = load_demo_units()
    with conn.transaction():
        conn.execute("CREATE TEMP TABLE water_users (LIKE public.water_users INCLUDING CONSTRAINTS INCLUDING INDEXES) ON COMMIT PRESERVE ROWS")
        conn.execute("INSERT INTO pg_temp.water_users SELECT * FROM public.water_users")
        with conn.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO pg_temp.water_users (id, name, industry, water_used, budget, geom)
                SELECT %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                WHERE NOT EXISTS (SELECT 1 FROM public.water_users WHERE name = %s)
            """, [(-1001 - index, unit["name"], unit["industry"], unit["water_used"],
                   unit["budget"], unit["lon"], unit["lat"], unit["name"])
                  for index, unit in enumerate(units)])
