"""Read-only live DB check of the connection-local demo inventory; no LLM calls."""
import csv
import io
import json
from collections import Counter
from unittest.mock import patch

from app.services.db import get_db
from app.services.budget_data import read_water_units, build_inspection
from app.services.demo_data import load_demo_units
from app.services.inspection_reports import create_report
from app.services.tools import query_water_users, get_budget_status, get_street_ranking, inspect_area, inspect_water_budget, find_nearby


def persistent_snapshot():
    with get_db(include_demo=False) as conn:
        return conn.execute('SELECT id, name, industry, water_used, budget, ST_AsText(geom) FROM public.water_users ORDER BY id').fetchall()


before = persistent_snapshot()
with patch('app.services.db.DEMO_WATER_UNITS', True):
    with get_db() as conn:
        units = read_water_units(conn)
        public_count = conn.execute('SELECT count(*) FROM public.water_users').fetchone()[0]
        assert public_count == len(before)
        assert conn.execute("SELECT has_table_privilege(current_user, 'public.water_users', 'INSERT')").fetchone()[0] is False
        assert {unit['name'] for unit in load_demo_units()} <= {unit['name'] for unit in units}
        assert all(unit['district'] != '未归属' and unit['street'] != '未归属' for unit in units)
        assert len(units) == len(before) + 32
        report = build_inspection(units)
    # Closing the overlay connection drops every demo row; a new one rebuilds it.
    with get_db() as conn:
        assert len(read_water_units(conn)) == len(units)
    districts = Counter(unit['district'] for unit in units)
    assert districts == {'通州区': 9, '大兴区': 9, '朝阳区': 9, '顺义区': 9}
    assert {key: report['summary'][key] for key in ('over_budget', 'near_limit', 'normal', 'invalid_data')} == {'over_budget': 9, 'near_limit': 10, 'normal': 13, 'invalid_data': 4}
    assert get_budget_status('通州运河装备厂（演示）')['data']['execution_rate'] == 165
    assert len(query_water_users('建筑业', limit=20)['data']) == 8
    assert sum(row['user_count'] for row in get_street_ranking()['data']) == 36
    district_report = inspect_water_budget(district='通州区', status_filter='over_budget')
    assert district_report['summary']['checked_count'] == 9 and len(district_report['data']) == 3
    ring = [[116.60, 39.65], [116.90, 39.65], [116.90, 39.95], [116.60, 39.95], [116.60, 39.65]]
    assert inspect_area(ring)['summary']['checked_count'] == 9
    assert any(row['name'].endswith('（演示）') for row in find_nearby('潮白河', 5)['data'])
    artifact = create_report(report)
    assert len(list(csv.reader(io.StringIO(artifact['csv'])))) == 37
    assert '（演示）' in artifact['markdown']
after = persistent_snapshot()
assert before == after, 'Persistent business rows changed unexpectedly'
print(json.dumps({'units': len(units), 'districts': districts, 'status_counts': {key: report['summary'][key] for key in ('over_budget', 'near_limit', 'normal', 'invalid_data')}, 'report_rows': 36, 'persistent_rows_unchanged': len(after), 'reader_still_cannot_insert': True}, ensure_ascii=False))
