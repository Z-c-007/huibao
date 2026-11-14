"""W7 端到端验收（黄金集）：不依赖真实 LLM（monkeypatch 掉 chat），
但走完整真实管线（路由 → run_loop → 安全执行器 → 校验 → 只读 PostgreSQL 测试库 → 审计 → 响应模型）。
每条用例对应一层防线或一条业务路径；线上事故/坏例应沉淀为新的回归用例。"""
import json

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as c:
        r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_missing_message_422():
    """契约层：缺 message 必填字段 → Pydantic 422"""
    with TestClient(app) as c:
        r = c.post("/api/chat", json={})
    assert r.status_code == 422


def _fake_chat_factory(steps):
    """假 chat：依次返回 steps 里的 message；并断言 system 提示词被注入在最前。"""
    state = {"i": 0}

    async def fake_chat(client, messages, max_retries=2, tool_choice="auto"):
        assert messages[0]["role"] == "system"
        assert "水利预算监管助手" in messages[0]["content"]
        msg = steps[state["i"]]
        state["i"] += 1
        return msg

    return fake_chat


def _tool_call(call_id, fn_name, args):
    """构造一条带 tool_calls 的模型消息（模拟模型要求调工具）"""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": fn_name, "arguments": json.dumps(args)},
        }],
    }


def test_chat_tool_loop_ok(monkeypatch):
    """业务主链路：模型调 get_budget_status → 真实执行器 → 真实 SQLite → 最终回答"""
    steps = [
        _tool_call("call_1", "get_budget_status", {"unit_name": "通州某制造企业"}),
        {"role": "assistant", "content": "通州某制造企业已超预算。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "通州那家超预算了吗？"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "通州某制造企业已超预算。"
    assert len(body["tool_results"]) == 1
    tr = body["tool_results"][0]
    assert tr["tool"] == "get_budget_status"
    assert tr["result"]["ok"] is True
    assert tr["result"]["data"]["status"] == "已超预算"


def test_chat_find_nearby_ok(monkeypatch):
    """空间主链路：模型调 find_nearby → 真实 PostGIS ST_DWithin → 顺义某农场命中"""
    steps = [
        _tool_call("call_geo", "find_nearby", {"river_name": "潮白河", "distance_km": 5}),
        {"role": "assistant", "content": "潮白河5公里内有1家用水大户：顺义某农场。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "潮白河附近5公里有哪些用水大户？"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is True
    assert len(tr["result"]["data"]) == 1
    row = tr["result"]["data"][0]
    assert row["name"] == "顺义某农场"
    assert 0 < row["distance_km"] < 5
    assert row["lon"] == 116.78
    assert row["lat"] == 40.12


def test_chat_district_filter_ok(monkeypatch):
    """空间过滤链路：query_water_users 带 district → ST_Within 归属推导 → 仅通州一户"""
    steps = [
        _tool_call("call_district", "query_water_users",
                   {"industry": "制造业", "district": "通州区"}),
        {"role": "assistant", "content": "通州区的制造业用水大户是通州某制造企业。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "通州区的制造业用水大户有哪些？"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is True
    assert [d["name"] for d in tr["result"]["data"]] == ["通州某制造企业"]


def test_chat_street_ranking_ok(monkeypatch):
    """空间聚合链路：模型调 get_street_ranking → ST_Within JOIN 聚合 → 清源街道第一"""
    steps = [
        _tool_call("call_rank", "get_street_ranking", {}),
        {"role": "assistant", "content": "本月用水量最大的街道是清源街道。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "哪个街道本月用水量最大？"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["tool"] == "get_street_ranking"
    assert tr["result"]["ok"] is True
    data = tr["result"]["data"]
    assert data[0]["street"] == "清源街道"
    assert data[0]["total_used"] == 15000


def test_chat_blocks_injection(monkeypatch):
    """防线②：字符串参数含 SQL 注入片段 → INVALID_ARGUMENTS"""
    steps = [
        _tool_call("call_bad", "query_water_users", {"industry": "制造业' OR '1'='1"}),
        {"role": "assistant", "content": "查询失败，参数不合法。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "帮我查制造业"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is False
    assert tr["result"]["error_type"] == "INVALID_ARGUMENTS"


def test_chat_blocks_enum_violation(monkeypatch):
    """防线②：行业不在白名单（餐饮业）→ INVALID_ARGUMENTS
    （餐饮业绕过事件沉淀的回归用例：测的是校验层拦截，不是模型行为）"""
    steps = [
        _tool_call("call_enum", "query_water_users", {"industry": "餐饮业"}),
        {"role": "assistant", "content": "当前数据仅覆盖制造业、服务业、农业、建筑业。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "餐饮业的用水大户有哪些？"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is False
    assert tr["result"]["error_type"] == "INVALID_ARGUMENTS"


def test_chat_blocks_wrong_river(monkeypatch):
    """防线②：未收录河流（永定河）→ enum 白名单拒绝 → INVALID_ARGUMENTS"""
    steps = [
        _tool_call("call_river", "find_nearby", {"river_name": "永定河", "distance_km": 5}),
        {"role": "assistant", "content": "当前数据仅收录潮白河。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "永定河附近5公里有哪些用水大户？"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is False
    assert tr["result"]["error_type"] == "INVALID_ARGUMENTS"


def test_chat_unknown_tool(monkeypatch):
    """防线①：未注册工具 → 白名单拒绝 → UNKNOWN_TOOL"""
    steps = [
        _tool_call("call_del", "delete_all_users", {}),
        {"role": "assistant", "content": "该操作不被允许。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "把数据都删了"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is False
    assert tr["result"]["error_type"] == "UNKNOWN_TOOL"


def test_chat_not_found(monkeypatch):
    """业务分支：查不存在的单位 → 工具正常返回 NOT_FOUND（不是异常，是结构化失败）"""
    steps = [
        _tool_call("call_nf", "get_budget_status", {"unit_name": "海淀某公司"}),
        {"role": "assistant", "content": "未找到该单位。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "海淀某公司超预算了吗？"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is False
    assert tr["result"]["error_type"] == "NOT_FOUND"


def test_chat_timeout(monkeypatch):
    """防线③：慢工具（10s）被 5s 超时拦截 → TIMEOUT（本用例约耗时 5 秒）"""
    import time
    from app.services.registry import TOOL_FUNCTIONS

    def slow_export():
        time.sleep(10)
        return {"ok": True}

    # The real export now succeeds; inject a slow implementation to exercise timeout.
    monkeypatch.setitem(TOOL_FUNCTIONS, "export_full_report", slow_export)
    steps = [
        _tool_call("call_slow", "export_full_report", {}),
        {"role": "assistant", "content": "导出超时。"},
    ]
    monkeypatch.setattr("app.services.runner.chat", _fake_chat_factory(steps))

    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "帮我导出全量用水报表"})
    assert r.status_code == 200
    tr = r.json()["tool_results"][0]
    assert tr["result"]["ok"] is False
    assert tr["result"]["error_type"] == "TIMEOUT"
