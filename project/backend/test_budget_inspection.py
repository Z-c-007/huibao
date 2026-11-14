"""Budget boundary and agent integration checks; no database writes or paid calls."""
import json
import unittest
from decimal import Decimal
from unittest.mock import patch

import httpx

from app.services.budget_data import classify_unit, build_inspection, read_water_units
from app.services.tools import get_budget_status
from app.services.validator import validate_args
from app.services.runner import run_stream


def row(name, used, budget, ident=1):
    return (ident, name, "制造业", Decimal(str(used)), Decimal(str(budget)), 116.72, 39.8, "通州区", "新华街道")


class Connection:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = None
        self.closed = False

    def execute(self, sql, params):
        self.sql, self.params = sql, params
        return self

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def close(self):
        self.closed = True


class BudgetTests(unittest.TestCase):
    def test_exact_thresholds_and_tiny_overrun(self):
        self.assertEqual(classify_unit(row("正常", 89.999, 100))["budget_status"], "normal")
        self.assertEqual(classify_unit(row("上限", 90, 100))["budget_status"], "near_limit")
        self.assertEqual(classify_unit(row("刚好", 100, 100))["budget_status"], "near_limit")
        unit = classify_unit(row("微超", 100.004, 100))
        self.assertEqual(unit["execution_rate"], 100)
        self.assertEqual(unit["budget_status"], "over_budget")
        self.assertAlmostEqual(unit["over_budget_amount"], 0.004)

    def test_invalid_budget_is_unknown_not_normal(self):
        for used, budget in [(1, 0), (0, 0), (-1, 100), (100, -1), ("NaN", 100), (100, "Infinity")]:
            with self.subTest(used=used, budget=budget):
                unit = classify_unit(row("待核实", used, budget))
                self.assertEqual(unit["budget_status"], "invalid_data")
                self.assertIsNone(unit["execution_rate"])
                json.dumps(unit, allow_nan=False)

    def test_decimal_amounts_are_preserved(self):
        unit = classify_unit(row("精度", "1000.125", "1000.05"))
        self.assertEqual(unit["water_used"], 1000.125)
        self.assertEqual(unit["budget"], 1000.05)
        self.assertEqual(unit["over_budget_amount"], 0.075)

    def test_sort_uses_ratio_before_rounding(self):
        units = [classify_unit(row("A微超", 100.003, 100)), classify_unit(row("Z微超", 100.004, 100)),
                 classify_unit(row("正常", 80, 100)), classify_unit(row("近上限", 95, 100))]
        report = build_inspection(units)
        self.assertEqual([unit["name"] for unit in report["data"]], ["Z微超", "A微超", "近上限", "正常"])

    def test_filtered_map_preserves_whole_scope_summary(self):
        units = [classify_unit(row("超预算", 120, 100)), classify_unit(row("近上限", 95, 100)),
                 classify_unit(row("正常", 70, 100)), classify_unit(row("待核实", 1, 0))]
        report = build_inspection(units, district="通州区", status_filter="over_budget", map_view="priority")
        self.assertEqual(report["summary"]["checked_count"], 4)
        self.assertEqual(report["summary"]["displayed_count"], 1)
        self.assertEqual(report["summary"]["near_limit"], 1)
        self.assertEqual(report["summary"]["invalid_data"], 1)
        self.assertEqual(report["summary"]["total_over_budget_amount"], 20)
        self.assertEqual([unit["name"] for unit in report["data"]], ["超预算"])
        self.assertEqual(report["map_view"], "priority")

    def test_empty_scope_is_complete_zero_result(self):
        report = build_inspection([], industry="建筑业")
        self.assertEqual(report["data"], [])
        for key in ("checked_count", "displayed_count", "over_budget", "normal", "near_limit", "invalid_data", "total_water_used", "total_budget"):
            self.assertEqual(report["summary"][key], 0)
        self.assertIsNone(report["summary"]["aggregate_execution_rate"])
        self.assertEqual(report["scope"]["industry"], "建筑业")

    def test_filters_are_bound_and_units_not_spatially_duplicated(self):
        conn = Connection([row("企业", 120, 100)])
        units = read_water_units(conn, district="通州区", industry="制造业")
        self.assertEqual(conn.params, ["通州区", "制造业"])
        self.assertNotIn("通州区", conn.sql)
        self.assertIn("ST_Covers", conn.sql)
        self.assertEqual(conn.sql.count("LATERAL"), 2)
        self.assertEqual(len(units), 1)

    def test_validator_rejects_unknown_scope_nan_and_invalid_options(self):
        self.assertIsNone(validate_args("inspect_water_budget", {}))
        self.assertIsNone(validate_args("inspect_water_budget", {"district": "通州区", "warning_percent": 95, "map_view": "priority"}))
        for args in [{"district": "海淀区"}, {"warning_percent": float("nan")}, {"warning_percent": float("inf")},
                     {"warning_percent": True}, {"warning_percent": 101}, {"status_filter": "unknown"}]:
            with self.subTest(args=args):
                self.assertIsNotNone(validate_args("inspect_water_budget", args))

    def test_single_unit_lookup_handles_zero_budget_and_matches_inspection(self):
        conn = Connection([(Decimal("1.25"), Decimal(0))])
        with patch("app.services.tools.get_db", return_value=conn):
            result = get_budget_status("企业")
        self.assertEqual(result["data"]["status"], "待核实")
        self.assertEqual(result["data"]["water_used"], 1.25)
        self.assertIsNone(result["data"]["rate"])
        self.assertTrue(conn.closed)


class AgentInspectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from test_regulatory import profile
        catalog = patch('app.services.regulatory.profiles', return_value={'企业': profile(120, 100)})
        catalog.start()
        self.addCleanup(catalog.stop)
    async def test_real_executor_inspection_and_streamed_results(self):
        calls = []
        conn = Connection([row("企业", 120, 100)])

        async def model(client, messages, thinking=True):
            calls.append([dict(message) for message in messages])
            if len(calls) == 1:
                yield {"type": "reasoning_delta", "text": "检查通州区的全部单位"}
                yield {"type": "message", "message": {"role": "assistant", "content": "", "reasoning_content": "检查通州区的全部单位",
                    "tool_calls": [{"id": "inspection", "type": "function", "function": {"name": "inspect_water_budget",
                        "arguments": '{"district":"通州区","status_filter":"over_budget","map_view":"priority"}'}}]}}
            else:
                report = json.loads(messages[-1]["content"])
                self.assertEqual(report["summary"]["over_budget"], 1)
                yield {"type": "content_delta", "text": "已检查1家，超预算1家。"}
                yield {"type": "message", "message": {"role": "assistant", "content": "已检查1家，超预算1家。", "reasoning_content": "已核实"}}

        with patch("app.services.runner.stream_chat", model), patch("app.services.tools.get_db", return_value=conn), patch("app.services.executor.audit"):
            events = [event async for event in run_stream(None, [{"role": "user", "content": "巡查通州区"}])]
        result = next(event for event in events if event["type"] == "tool_result")
        self.assertEqual(result["tool"], "inspect_water_budget")
        self.assertEqual(result["result"]["data"][0]["execution_rate"], 120)
        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(conn.closed)
        self.assertEqual(conn.params, ["通州区"])
        self.assertEqual(calls[1][2]["reasoning_content"], "检查通州区的全部单位")

    async def test_inventory_endpoint_returns_budget_inventory(self):
        from app.main import app
        conn = Connection([row("未建档企业", 120, 100)])
        with patch("app.services.map_data.get_db", return_value=conn):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/map/water-users")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["summary"]["checked_count"], 1)
        self.assertEqual(body["data"][0]["budget_status"], "invalid_data")
        self.assertIsNone(body['data'][0]['execution_rate'])
        self.assertIn('未关联', body['data'][0]['data_issues'][0])
        self.assertEqual(body["data"][0]["lon"], 116.72)
        self.assertTrue(conn.closed)


if __name__ == "__main__":
    unittest.main()
