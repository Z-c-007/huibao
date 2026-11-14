"""Opt-in read-only checks of map actions, selected-object grounding and area exports.

Uses several short live model requests through the current Vite proxy.
"""
import csv
import io
import json

import httpx

BASE = "http://127.0.0.1:5173"
RING = [[116.68, 39.76], [116.76, 39.76], [116.76, 39.86], [116.68, 39.86], [116.68, 39.76]]


def ask(client, prompt, context, history=None):
    results, next_history = [], None
    with client.stream("POST", BASE + "/api/chat/stream", json={"message": prompt, "history": history or [], "thinking": True, "map_context": context}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data:"):
                continue
            event = json.loads(line[5:])
            if event["type"] == "error":
                raise RuntimeError(event["message"])
            if event["type"] == "tool_result":
                assert event["result"].get("ok"), event["result"]
                results.append(event)
            if event["type"] == "done":
                next_history = event["history"]
    assert next_history and results
    print(json.dumps({"tools": [result["tool"] for result in results], "history_messages": len(next_history)}), flush=True)
    return results, next_history


def main():
    with httpx.Client(timeout=90) as client:
        response = client.post(BASE + "/api/map/area-analysis", json={"area": {"coordinates": RING}})
        response.raise_for_status()
        area = response.json()
        assert area["summary"]["checked_count"] == 1
        assert area["data"][0]["name"] == "通州某制造企业"
        print(json.dumps({"area_summary": area["summary"]}), flush=True)
        edge = [[116.72, 39.8], [116.76, 39.8], [116.76, 39.86], [116.72, 39.86], [116.72, 39.8]]
        boundary = client.post(BASE + "/api/map/area-analysis", json={"area": {"coordinates": edge}})
        boundary.raise_for_status()
        assert boundary.json()["summary"]["checked_count"] == 1
        bad = client.post(BASE + "/api/map/area-analysis", json={"area": {"coordinates": RING[:-1]}})
        assert bad.status_code == 422
        context = {"available": True, "selected_unit": "通州某制造企业"}
        results, history = ask(client, "这个单位是否超预算？请查询预算并定位它，简短回答。", context)
        budget = next(result["result"]["data"] for result in results if result["tool"] == "get_budget_status")
        assert budget["unit"] == "通州某制造企业" and budget["execution_rate"] == 120
        location = next(result["result"] for result in results if result["tool"] == "locate_water_unit")
        assert location["data"][0]["lon"] == 116.72
        results, history = ask(client, "隐藏河道图层，只显示当前范围的超预算单位，不要重新巡查。简短回答。", context, history)
        assert any(result["result"].get("action") == "set_layer" and result["result"].get("visibility") == "hide" for result in results)
        assert any(result["result"].get("action") == "filter_units" and result["result"].get("status") == "over_budget" for result in results)
        results, _ = ask(client, "回到全库总览，清除选中对象和筛选。", context, history)
        assert any(result["result"].get("action") == "reset_map" for result in results)
        results, _ = ask(client, "分析当前圈选区域的用水预算，并生成这个范围的巡查简报和CSV清单供下载，简短回答。", {"available": True, "area": {"coordinates": RING}})
        assert any(result["tool"] == "analyze_selected_area" for result in results)
        exported = next(result["result"] for result in results if result["tool"] == "generate_inspection_report")
        assert exported["summary"]["checked_count"] == 1 and exported["area"]["coordinates"][0] == RING
        rows = list(csv.reader(io.StringIO(exported["report"]["csv"])))
        assert len(rows) == 2 and rows[1][0] == "通州某制造企业"
        assert "12,000" in exported["report"]["markdown"]
        print(json.dumps({"report_markdown_chars": len(exported["report"]["markdown"]), "csv_rows": len(rows) - 1, "area_boundary_included": True}), flush=True)


if __name__ == "__main__":
    main()
