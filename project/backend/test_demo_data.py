"""Fast checks for optional demo inventory; no persistent DB changes."""
import unittest
from collections import Counter
from contextlib import nullcontext
from unittest.mock import patch, MagicMock

from app.services.demo_data import load_demo_units, install_demo_inventory
from app.services.budget_data import evaluate_budget
from app.services.db import get_db


class DemoInventoryTests(unittest.TestCase):
    def test_sample_coverage_and_unique_locations(self):
        units = load_demo_units()
        self.assertEqual(len(units), 32)
        self.assertEqual(Counter(unit['industry'] for unit in units),
                         {'制造业': 8, '服务业': 8, '农业': 8, '建筑业': 8})
        self.assertEqual(len({(unit['lon'], unit['lat']) for unit in units}), 32)
        self.assertEqual(Counter(evaluate_budget(unit['water_used'], unit['budget'])['budget_status'] for unit in units),
                         {'over_budget': 8, 'near_limit': 8, 'normal': 12, 'invalid_data': 4})

    def test_overlay_only_writes_to_temporary_table_with_bound_values(self):
        conn = MagicMock()
        conn.transaction.return_value = nullcontext()
        cursor = conn.cursor.return_value.__enter__.return_value
        install_demo_inventory(conn)
        sql, rows = cursor.executemany.call_args.args
        self.assertIn('INSERT INTO pg_temp.water_users', sql)
        self.assertIn('WHERE NOT EXISTS', sql)
        self.assertNotIn('运河装备', sql)
        self.assertEqual(len(rows), 32)
        self.assertEqual(len({row[0] for row in rows}), 32)
        self.assertTrue(all(row[0] < 0 for row in rows))
        self.assertFalse(any('INSERT INTO public.' in call.args[0] for call in conn.execute.call_args_list))

    def test_disabled_mode_and_base_map_skip_overlay(self):
        conn = MagicMock()
        with patch('app.services.db.psycopg.connect', return_value=conn), patch('app.services.db.install_demo_inventory') as install:
            with patch('app.services.db.DEMO_WATER_UNITS', False):
                self.assertIs(get_db(), conn)
            with patch('app.services.db.DEMO_WATER_UNITS', True):
                self.assertIs(get_db(include_demo=False), conn)
            install.assert_not_called()

    def test_failed_overlay_closes_connection(self):
        conn = MagicMock()
        with patch('app.services.db.psycopg.connect', return_value=conn), patch('app.services.db.DEMO_WATER_UNITS', True), patch('app.services.db.install_demo_inventory', side_effect=ValueError('invalid sample')):
            with self.assertRaises(ValueError):
                get_db()
        conn.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
