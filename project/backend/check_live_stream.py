"""Opt-in live DeepSeek smoke check (one short request; no database queries).

Run: .venv/Scripts/python.exe check_live_stream.py
Prints only response counts and the short answer, never credentials/reasoning.
"""
import asyncio
import json

import httpx

from app.core.config import LLM_API_KEY, LLM_MODEL
from app.services.runner import run_stream


async def main():
    if not LLM_API_KEY:
        raise RuntimeError("未配置模型 API Key")
    reasoning = ""
    answer = ""
    completed = False
    async with asyncio.timeout(60):
        async with httpx.AsyncClient(timeout=30) as client:
            async for event in run_stream(client, [{
                "role": "user", "content": "1+1等于多少？请用一句话回答，不需要查询业务数据。",
            }], thinking=True):
                if event["type"] == "reasoning_delta":
                    reasoning += event["text"]
                elif event["type"] == "content_delta":
                    answer += event["text"]
                elif event["type"] == "done":
                    completed = True
    result = {"model": LLM_MODEL, "completed": completed,
              "reasoning_chars": len(reasoning), "answer": answer[:120]}
    print(json.dumps(result, ensure_ascii=False))
    if not completed or not reasoning or not answer:
        raise RuntimeError("模型未同时返回思考文本和回答")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.HTTPStatusError as error:
        print(f"Live check failed: HTTP {error.response.status_code}")
        raise SystemExit(1) from None
