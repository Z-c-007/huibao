"""LLM 调用：DeepSeek 兼容 API，含重试机制。"""
import asyncio
import json
import sys

import httpx

from ..core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from .registry import TOOLS

# Windows 控制台默认 GBK，日志含中文会触发 UnicodeEncodeError，强制 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def chat(client, messages, max_retries=2, tool_choice="auto"):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
                json={"model": LLM_MODEL, "messages": messages, "tools": TOOLS, "tool_choice": tool_choice},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]
        except httpx.HTTPStatusError as exc:
            # 4xx 是请求本身有问题（含审核拦截），重试无意义，直接抛出
            print(f"[HTTP 错误] {exc.response.status_code}: {exc.response.text[:200]}")
            raise
        except (httpx.TransportError, KeyError, json.JSONDecodeError) as exc:
            # 只有瞬时故障（网络、超时、响应结构异常）才重试
            last_error = exc
            print(f"[重试] 第 {attempt + 1} 次请求失败: {exc}")
            if attempt < max_retries:
                await asyncio.sleep(1 + attempt)
    raise last_error


async def stream_chat(client, messages, thinking=True, max_retries=2):
    """Forward real DeepSeek deltas; accumulate fragmented tool calls before execution.

    Reasoning stays in the assistant message for subsequent tool-call requests.
    Never retry after publishing a delta: that would duplicate visible output.
    """
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "stream": True,
        "thinking": {"type": "enabled" if thinking else "disabled"},
    }
    published = False
    for attempt in range(max_retries + 1):
        content, reasoning, calls = "", "", {}
        finished = False
        finish_reason = None
        try:
            async with client.stream(
                "POST", f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        finished = True
                        break
                    chunk = json.loads(data)
                    if chunk.get("error"):
                        raise RuntimeError("模型服务返回了错误，请稍后重试。")
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta", {})
                    if delta.get("reasoning_content"):
                        text = delta["reasoning_content"]
                        reasoning += text
                        published = True
                        yield {"type": "reasoning_delta", "text": text}
                    if delta.get("content"):
                        text = delta["content"]
                        content += text
                        published = True
                        yield {"type": "content_delta", "text": text}
                    for fragment in delta.get("tool_calls") or []:
                        index = fragment["index"]
                        call = calls.setdefault(index, {
                            "id": "", "type": "function",
                            "function": {"name": "", "arguments": ""},
                        })
                        if fragment.get("id"):
                            call["id"] = fragment["id"]
                        function = fragment.get("function", {})
                        call["function"]["name"] += function.get("name") or ""
                        call["function"]["arguments"] += function.get("arguments") or ""
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
                        finished = True
            if not finished:
                raise httpx.ReadError("模型响应流意外中断。")
            if finish_reason not in (None, "stop", "tool_calls"):
                raise RuntimeError("模型输出未完整结束，请缩小问题范围后重试。")
            if not content and not calls:
                raise RuntimeError("模型未返回回答，请重试。")
            message = {"role": "assistant", "content": content,
                       "reasoning_content": reasoning}
            if calls:
                ordered = [calls[index] for index in sorted(calls)]
                if any(not call["id"] or not call["function"]["name"] for call in ordered):
                    raise RuntimeError("模型返回的工具调用不完整，请重试。")
                message["tool_calls"] = ordered
            yield {"type": "message", "message": message}
            return
        except (httpx.TransportError, json.JSONDecodeError):
            if published or attempt == max_retries:
                raise
            await asyncio.sleep(1 + attempt)
