"""安全执行器：白名单 → 校验 → 超时 → 审计。"""
import asyncio
import time

from .audit import audit
from .registry import TOOL_FUNCTIONS
from .validator import validate_args
from .agent_context import get_context


async def run_tool(fn_name, args):
    start = time.perf_counter()

    fn = TOOL_FUNCTIONS.get(fn_name)
    if fn is None:
        result = {"ok": False, "error": f"工具 {fn_name} 未注册，已拒绝执行", "error_type": "UNKNOWN_TOOL"}
    else:
        error = validate_args(fn_name, args)
        if error is not None:
            result = {"ok": False, "error": error, "error_type": "INVALID_ARGUMENTS"}
        else:
            try:
                result = await asyncio.wait_for(asyncio.to_thread(fn, **args), timeout=5)
            except TimeoutError:
                result = {"ok": False, "error": f"工具 {fn_name} 执行超时（>5s）", "error_type": "TIMEOUT"}
            except Exception as exc:
                result = {"ok": False, "error": f"执行出错: {exc}", "error_type": "EXECUTION_ERROR"}

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    if result.get("ok") and "summary" in result and "scope" in result:
        get_context().latest_report = result
    audit(fn_name, args, result, elapsed_ms)
    return result
