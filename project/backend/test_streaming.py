"""Streaming regressions without a live model, credentials or database writes.

Run: .venv/Scripts/python.exe -m unittest test_streaming -v
Kept outside tests/ because that suite automatically resets the PostgreSQL seed.
"""
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.llm import stream_chat
from app.services.runner import run_stream


def chunk(delta=None, finish=None):
    return "data: " + json.dumps({"choices": [{"delta": delta or {}, "finish_reason": finish}]})


class Response:
    def __init__(self, lines):
        self.lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        pass

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class Client:
    def __init__(self, lines):
        self.lines = lines
        self.requests = []

    def stream(self, method, url, **kwargs):
        self.requests.append(kwargs["json"])
        return Response(self.lines)


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_reasoning_and_fragmented_tool_calls(self):
        client = Client([
            ": keep-alive", "data: {\"choices\": []}",
            chunk({"reasoning_content": "需要查询"}),
            chunk({"reasoning_content": "用水单位。"}),
            chunk({"tool_calls": [{"index": 0, "id": "call_1", "function": {
                "name": "query_water_users", "arguments": '{"industry":'}}]}),
            chunk({"tool_calls": [{"index": 0, "function": {"arguments": '"制造业"}'}}]}),
            chunk(finish="tool_calls"), "data: [DONE]",
        ])
        events = [event async for event in stream_chat(client, [{"role": "user", "content": "查询"}])]
        self.assertEqual([event["text"] for event in events[:-1]], ["需要查询", "用水单位。"])
        message = events[-1]["message"]
        self.assertEqual(message["reasoning_content"], "需要查询用水单位。")
        self.assertEqual(message["tool_calls"][0]["function"]["arguments"], '{"industry":"制造业"}')
        self.assertEqual(client.requests[0]["thinking"], {"type": "enabled"})

    async def test_non_thinking_answer(self):
        client = Client([chunk({"content": "回答"}), chunk(finish="stop"), "data: [DONE]"])
        events = [event async for event in stream_chat(client, [], thinking=False)]
        self.assertEqual(events[0], {"type": "content_delta", "text": "回答"})
        self.assertEqual(client.requests[0]["thinking"], {"type": "disabled"})

    async def test_interruption_does_not_replay_published_text(self):
        client = Client([chunk({"reasoning_content": "部分思考"})])
        with self.assertRaises(httpx.ReadError):
            _ = [event async for event in stream_chat(client, [])]
        self.assertEqual(len(client.requests), 1)

    async def test_truncated_tool_arguments_are_not_executed(self):
        client = Client([
            chunk({"tool_calls": [{"index": 0, "id": "call", "function": {
                "name": "get_budget_status", "arguments": '{"unit_name":'}}]}),
            chunk(finish="length"), "data: [DONE]",
        ])
        with self.assertRaisesRegex(RuntimeError, "未完整"):
            _ = [event async for event in stream_chat(client, [])]

    async def test_tool_loop_preserves_reasoning_and_history(self):
        seen = []

        async def fake_stream(client, messages, thinking=True):
            seen.append([dict(message) for message in messages])
            if len(seen) == 1:
                yield {"type": "reasoning_delta", "text": "先核查预算"}
                yield {"type": "message", "message": {
                    "role": "assistant", "content": "", "reasoning_content": "先核查预算",
                    "tool_calls": [{"id": "call", "type": "function", "function": {
                        "name": "get_budget_status", "arguments": '{"unit_name":"通州某制造企业"}'}}],
                }}
            else:
                yield {"type": "content_delta", "text": "已超预算"}
                yield {"type": "message", "message": {
                    "role": "assistant", "content": "已超预算", "reasoning_content": "结果已核实",
                }}

        with patch("app.services.runner.stream_chat", fake_stream), patch(
            "app.services.runner.run_tool", AsyncMock(return_value={"ok": True, "data": {"rate": 1.2}})
        ) as tool:
            events = [event async for event in run_stream(None, [{"role": "user", "content": "超预算了吗"}])]
        tool.assert_awaited_once_with("get_budget_status", {"unit_name": "通州某制造企业"})
        self.assertEqual(seen[1][2]["reasoning_content"], "先核查预算")
        self.assertEqual(seen[1][3]["role"], "tool")
        self.assertEqual(events[-1]["type"], "done")
        history = events[-1]["history"]
        self.assertEqual([m["role"] for m in history], ["user", "assistant", "tool", "assistant"])
        self.assertEqual(history[-1]["reasoning_content"], "结果已核实")
        types = [event["type"] for event in events]
        self.assertLess(types.index("tool_result"), types.index("content_delta"))

    async def test_bad_argument_object_and_round_limit(self):
        async def loop(client, messages, thinking=True):
            yield {"type": "message", "message": {
                "role": "assistant", "content": "", "reasoning_content": "",
                "tool_calls": [{"id": "call", "function": {"name": "get_street_ranking", "arguments": "[]"}}],
            }}

        results = []
        with patch("app.services.runner.stream_chat", loop), patch("app.services.runner.run_tool", AsyncMock()) as tool:
            with self.assertRaisesRegex(RuntimeError, "步骤已达上限"):
                async for event in run_stream(None, []):
                    if event["type"] == "tool_result":
                        results.append(event)
        tool.assert_not_awaited()
        self.assertEqual(len(results), 8)
        self.assertTrue(all(event["result"]["error_type"] == "BAD_JSON" for event in results))

    async def test_route_emits_sse_and_safe_error(self):
        from app.main import app

        async def fail(client, messages, thinking=True):
            yield {"type": "reasoning_delta", "text": "思考文本"}
            raise httpx.ReadError("internal connection details")

        with patch("app.api.routes.chat.run_stream", fail):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/chat/stream", json={"message": "测试"})
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertEqual(response.headers["x-accel-buffering"], "no")
        self.assertIn("思考文本", response.text)
        self.assertIn('"type":"error"', response.text)
        self.assertNotIn("internal connection details", response.text)


if __name__ == "__main__":
    unittest.main()
