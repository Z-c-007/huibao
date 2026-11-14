"""对话路由：POST /api/chat，接收 ChatRequest，返回 ChatResponse"""
import asyncio
import json
from contextlib import aclosing

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ...schemas.chat import ChatRequest, ChatResponse
from ...services.runner import run_loop, run_stream
from ...services.report_drafts import get_draft
from fastapi import HTTPException

router = APIRouter(tags=["chat"])


def check_report(req):
    if req.report_context:
        try:
            get_draft(req.report_context.report_id, req.report_context.version)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    check_report(req)
    messages = [{"role": "user", "content": req.message}]
    if req.history:
        messages = req.history + messages

    async with httpx.AsyncClient(timeout=30) as client:
        kwargs = {'map_context': req.map_context}
        if req.report_context is not None:
            kwargs['report_context'] = req.report_context
        answer, tool_results = await run_loop(client, messages, **kwargs)

    return ChatResponse(answer=answer, tool_results=tool_results)


@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest, request: Request):
    check_report(req)
    messages = req.history + [{"role": "user", "content": req.message}]

    async def events():
        try:
            async with asyncio.timeout(300):
                async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=15)) as client:
                    kwargs = {"thinking": req.thinking}
                    if req.map_context is not None:
                        kwargs["map_context"] = req.map_context
                    if req.report_context is not None:
                        kwargs['report_context'] = req.report_context
                    async with aclosing(run_stream(client, messages, **kwargs)) as stream:
                        async for event in stream:
                            if await request.is_disconnected():
                                return
                            yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            error = ("模型鉴权失败，请检查 API Key。" if status in (401, 403)
                     else "模型服务暂时不可用，请稍后重试。" if status >= 500
                     else f"模型请求失败（HTTP {status}），请检查模型配置或稍后重试。")
            yield "data: " + json.dumps({"type": "error", "message": error}, ensure_ascii=False) + "\n\n"
        except (TimeoutError, httpx.TimeoutException):
            yield 'data: {"type":"error","message":"分析超时，请缩小问题范围后重试。"}\n\n'
        except httpx.TransportError:
            yield 'data: {"type":"error","message":"模型连接中断，请重试。"}\n\n'
        except RuntimeError as exc:
            yield "data: " + json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n\n"
        except Exception:
            yield 'data: {"type":"error","message":"服务处理失败，请检查后端日志后重试。"}\n\n'

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })
