"""Opt-in checks through the running Vite proxy; reads current data, no seed writes.

Uses the configured model for three short inspection prompts (consumes tokens).
"""
import json

import httpx


def run():
    base = "http://127.0.0.1:5173"
    with httpx.Client(timeout=90) as client:
        response = client.get(base + "/api/map/water-users")
        response.raise_for_status()
        inventory = response.json()
        assert inventory["ok"] and len(inventory["data"]) == inventory["summary"]["checked_count"]
        print(json.dumps({"inventory": inventory["summary"]}), flush=True)
        cases = [
            ("请巡查全部已入库用水单位的预算，把超预算单位在地图标红，并按超额比例排序，简短报告。", {"status_filter": "all", "map_view": "overview"}),
            ("巡查通州区，只显示超预算单位，并定位超额比例最高的单位。简短报告。",
             {"district": "通州区", "status_filter": "over_budget", "map_view": "priority"}),
            ("巡查建筑业用水单位的预算。没有单位时如实说明，简短回答。", {"industry": "建筑业"}),
        ]
        for prompt, required in cases:
            reports = []
            thinking_chars = 0
            answer_chars = 0
            done = False
            with client.stream("POST", base + "/api/chat/stream", json={"message": prompt, "thinking": True, "map_context": {"available": True}}) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    event = json.loads(line[5:])
                    if event["type"] == "error":
                        raise RuntimeError(event["message"])
                    if event["type"] == "reasoning_delta":
                        thinking_chars += len(event["text"])
                    if event["type"] == "content_delta":
                        answer_chars += len(event["text"])
                    if event["type"] == "tool_result" and event["tool"] == "inspect_water_budget":
                        assert event["result"]["ok"], event["result"]
                        assert all((event["result"].get(key) if key in ("status_filter", "map_view") else event["args"].get(key)) == value for key, value in required.items()), event["args"]
                        reports.append(event["result"])
                    if event["type"] == "done":
                        done = True
            assert done and thinking_chars and answer_chars and reports
            report = reports[-1]
            assert all("lon" in unit and "budget_status" in unit for unit in report["data"])
            if required.get("status_filter") == "all":
                assert report["summary"]["checked_count"] == inventory["summary"]["checked_count"]
                assert len(report["data"]) == inventory["summary"]["checked_count"]
            if required.get("status_filter") == "over_budget":
                assert all(unit["budget_status"] == "over_budget" for unit in report["data"])
            print(json.dumps({"scope": report["scope"], "summary": report["summary"], "map_view": report["map_view"],
                              "reasoning_chars": thinking_chars, "answer_chars": answer_chars}), flush=True)


if __name__ == "__main__":
    run()
