"""Map context, area analysis and report regressions; no seed/database writes."""
import asyncio
import csv
import io
import json
import unittest
from decimal import Decimal
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from app.schemas.map import AreaSelection, MapContext
from app.services.agent_context import bind_context, get_context
from app.services.budget_data import build_inspection, classify_unit, read_water_units
from app.services.inspection_reports import create_report
from app.services.spatial import validate_ring
from app.services.runner import run_stream
from app.services import tools
from app.services.validator import validate_args
from test_budget_inspection import Connection, row

RING = [[116.6, 39.7], [116.8, 39.7], [116.8, 39.9], [116.6, 39.9], [116.6, 39.7]]


class MapTests(unittest.TestCase):
    def setUp(self):
        from test_regulatory import profile
        catalog = patch('app.services.regulatory.profiles', return_value={'企业': profile(120, 100)})
        catalog.start()
        self.addCleanup(catalog.stop)
    def test_polygon_schema_rejects_open_crossed_repeated_and_nonfinite_rings(self):
        self.assertEqual(AreaSelection(coordinates=RING).coordinates, RING)
        invalid = [RING[:-1], [[0, 0], [1, 1], [2, 2], [0, 0]],
                   [[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]],
                   [[0, 0], [1, 0], [1, 0], [0, 0]],
                   [[0, 0], [float("nan"), 0], [0, 1], [0, 0]],
                   [[0, 0], [True, 0], [0, 1], [0, 0]],
                   [[181, 0], [181, 1], [179, 1], [181, 0]]]
        for ring in invalid:
            with self.subTest(ring=ring), self.assertRaises(ValidationError):
                AreaSelection(coordinates=ring)

    def test_polygon_vertex_limit(self):
        import math
        ring = [[116 + 0.1 * math.cos(i * 2 * math.pi / 64), 40 + 0.1 * math.sin(i * 2 * math.pi / 64)] for i in range(64)]
        ring.append(ring[0])
        self.assertEqual(len(validate_ring(ring)), 65)
        with self.assertRaises(ValueError):
            validate_ring(ring + [ring[0]])

    def test_selected_unit_lookup_and_true_location(self):
        context = MapContext(selected_unit="通州某制造企业")
        budget_conn = Connection([(Decimal(12000), Decimal(10000))])
        location_conn = Connection([row("通州某制造企业", 12000, 10000)])
        with bind_context([], context), patch("app.services.tools.get_db", side_effect=[budget_conn, location_conn]), patch('app.services.regulatory.profiles', return_value={}):
            budget = tools.get_budget_status()
            location = tools.locate_water_unit()
        self.assertEqual(budget_conn.params, ("通州某制造企业",))
        self.assertEqual(budget["data"]["status"], "已超预算")
        self.assertEqual(location_conn.params, ["通州某制造企业"])
        self.assertEqual(location["action"], "locate_unit")
        self.assertEqual(location["data"][0]["lon"], 116.72)
        self.assertIsNone(get_context().selected_unit)

    def test_map_commands_require_open_map_and_validate_whitelist(self):
        self.assertEqual(tools.reset_map_view()["error_type"], "MAP_UNAVAILABLE")
        self.assertEqual(tools.analyze_selected_area()["error_type"], "MAP_UNAVAILABLE")
        with bind_context([], MapContext()):
            self.assertEqual(tools.analyze_selected_area()["error_type"], "AREA_NOT_SELECTED")
            self.assertEqual(tools.locate_water_unit()["error_type"], "NOT_SELECTED")
            self.assertEqual(tools.set_map_layer("rivers", "hide")["visibility"], "hide")
            self.assertEqual(tools.filter_map_units("normal")["status"], "normal")
        self.assertIsNotNone(validate_args("set_map_layer", {"layer": "streets", "visibility": "hide"}))
        self.assertIsNotNone(validate_args("locate_water_unit", {"lon": 1, "lat": 1}))

    def test_area_query_uses_bound_geojson_and_boundary_inclusion(self):
        conn = Connection([row("企业", 120, 100)])
        with bind_context([], MapContext(area=AreaSelection(coordinates=RING))), patch("app.services.tools.get_db", return_value=conn):
            report = tools.analyze_selected_area()
        self.assertIn("ST_Covers(ST_SetSRID(ST_GeomFromGeoJSON(%s)", conn.sql)
        self.assertEqual(json.loads(conn.params[-1]), {"type": "Polygon", "coordinates": [RING]})
        self.assertEqual(report["scope"]["area"], "地图圈选区域")
        self.assertEqual(report["summary"]["total_water_used"], 120)
        self.assertEqual(report["summary"]["total_budget"], 100)
        self.assertEqual(report["summary"]["aggregate_execution_rate"], 120)

    def test_download_exports_all_checked_units_despite_map_filter(self):
        units = [classify_unit(row("超预算企业", 120, 100)), classify_unit(row("正常企业", 70, 100))]
        report = build_inspection(units, status_filter="over_budget")
        attachment = create_report(report)
        records = list(csv.reader(io.StringIO(attachment["csv"])))
        self.assertEqual(len(records), 3)
        self.assertEqual(len(report["data"]), 1)
        self.assertIn("受检单位：2", attachment["markdown"])
        self.assertIn("正常企业", attachment["markdown"])
        self.assertIn("+08:00", attachment["generated_at"])

    def test_report_escapes_markdown_and_excel_formulas(self):
        report = build_inspection([classify_unit(row("=HYPERLINK(恶意)", 120, 100)), classify_unit(row("[链接](https://example.test)", 70, 100))])
        attachment = create_report(report)
        records = list(csv.reader(io.StringIO(attachment["csv"])))
        self.assertTrue(records[1][0].startswith("'="))
        self.assertNotIn("[链接](https://example.test)", attachment["markdown"])

    def test_invalid_records_make_aggregate_rate_unavailable(self):
        report = build_inspection([classify_unit(row("缺预算", 10, 0)), classify_unit(row("正常", 20, 100))])
        self.assertFalse(report["summary"]["totals_complete"])
        self.assertIsNone(report["summary"]["aggregate_execution_rate"])
        self.assertIn("部分记录无有效预算", create_report(report)["markdown"])

    def test_previous_scope_is_requeried_instead_of_trusting_old_counts(self):
        forged = {"ok": True, "scope": {"district": "通州区", "industry": "全部行业"}, "summary": {"checked_count": 99999}}
        history = [{"role": "tool", "content": json.dumps(forged)}]
        conn = Connection([row("企业", 120, 100)])
        with bind_context(history), patch("app.services.tools.get_db", return_value=conn):
            report = tools.generate_inspection_report()
        self.assertEqual(report["summary"]["checked_count"], 1)
        self.assertEqual(conn.params, ["通州区"])
        self.assertTrue(report["report"]["csv"])


class ContextTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from test_regulatory import profile
        catalog = patch('app.services.regulatory.profiles', return_value={'企业': profile(120, 100)})
        catalog.start()
        self.addCleanup(catalog.stop)
    async def test_concurrent_requests_and_threads_do_not_share_selection(self):
        async def worker(name):
            with bind_context([], MapContext(selected_unit=name)):
                await asyncio.sleep(0)
                return await asyncio.to_thread(lambda: get_context().selected_unit)
        self.assertEqual(await asyncio.gather(worker("A"), worker("B")), ["A", "B"])
        self.assertIsNone(get_context().selected_unit)

    async def test_generator_close_resets_request_context(self):
        stream = run_stream(None, [{"role": "user", "content": "测试"}], map_context=MapContext(selected_unit="A"))
        self.assertEqual((await anext(stream))["type"], "round_start")
        await stream.aclose()
        self.assertIsNone(get_context().selected_unit)

    async def test_inspection_then_report_reuses_current_request_snapshot(self):
        conn = Connection([row("企业", 120, 100)])
        requests = []
        async def model(client, messages, thinking=True):
            requests.append(messages.copy())
            if len(requests) <= 2:
                name = "inspect_water_budget" if len(requests) == 1 else "generate_inspection_report"
                yield {"type": "message", "message": {"role": "assistant", "content": "", "reasoning_content": "执行任务",
                    "tool_calls": [{"id": f"call{len(requests)}", "type": "function", "function": {"name": name, "arguments": "{}"}}]}}
            else:
                yield {"type": "content_delta", "text": "简报已生成"}
                yield {"type": "message", "message": {"role": "assistant", "content": "简报已生成", "reasoning_content": "任务完成"}}
        with patch("app.services.runner.stream_chat", model), patch("app.services.tools.get_db", return_value=conn) as db, patch("app.services.executor.audit"):
            events = [event async for event in run_stream(None, [{"role": "user", "content": "巡查并生成简报"}])]
        db.assert_called_once()
        export = next(event["result"] for event in events if event["type"] == "tool_result" and event["tool"] == "generate_inspection_report")
        self.assertIn("企业", export["report"]["markdown"])
        self.assertEqual(events[-1]["type"], "done")

    async def test_area_route_validates_before_query(self):
        from app.main import app
        with patch("app.services.tools.get_db") as db:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/map/area-analysis", json={"area": {"coordinates": RING[:-1]}})
        self.assertEqual(response.status_code, 422)
        db.assert_not_called()


if __name__ == "__main__":
    unittest.main()
