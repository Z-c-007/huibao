import asyncio
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv

# Windows 控制台默认 GBK，模型输出含 emoji（如 ⚠️ \u26a0）会触发 UnicodeEncodeError，强制 UTF-8 输出
sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

DB_PATH = "data/water.db"
AUDIT_PATH = "data/audit.jsonl"

ALLOWED_INDUSTRIES = ("制造业", "服务业", "农业", "建筑业")
FORBIDDEN_CHARS = ("'", '"', ";", "--")
# ---------- 1. 数据库层：建库用写权限，查询用只读 ----------

def init_db():
    """第一次运行时建库并灌入模拟数据（只有初始化才用写权限）"""
    if os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE water_users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT NOT NULL,
            water_used INTEGER NOT NULL,
            budget INTEGER NOT NULL
        )
    """)
    conn.executemany(
        "INSERT INTO water_users (name, industry, water_used, budget) VALUES (?, ?, ?, ?)",
        [
            ("通州某制造企业", "制造业", 12000, 10000),
            ("大兴某制造企业", "制造业", 15000, 20000),
            ("朝阳某酒店", "服务业", 3000, 4000),
            ("顺义某农场", "农业", 800, 1200),
        ],
    )
    conn.commit()
    conn.close()


def get_db():
    """业务查询一律走只读连接（最小权限）"""
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

# ---------- 2. 工具层：SQL 固定写死，模型只能填参数值 ----------

def query_water_users(industry, limit=10):
    # """limit 是默认参数：模型省略时自动用 10"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT name, water_used, budget FROM water_users WHERE industry = ? LIMIT ?",
            (industry, limit),
        ).fetchall()
        return {"ok": True, "data": [{"name": r[0], "water_used": r[1], "budget": r[2]} for r in rows]}
    finally:
        conn.close()


def get_budget_status(unit_name):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT water_used, budget FROM water_users WHERE name = ?",
            (unit_name,),
        ).fetchone()
        if row is None:
            return {"ok": False, "error": f"未找到单位: {unit_name}", "error_type": "NOT_FOUND"}
        water_used, budget = row
        rate = round(water_used / budget, 2)
        return {
            "ok": True,
            "data": {
                "unit": unit_name,
                "water_used": water_used,
                "budget": budget,
                "rate": rate,
                "status": "已超预算" if rate > 1 else "正常",
            },
        }
    finally:
        conn.close()


def export_full_report():
    """模拟一个很慢的耗时操作：导出全量用水报表"""
    time.sleep(10)
    return {"ok": True, "data": "报表导出完成"}


TOOL_FUNCTIONS = {
    "query_water_users": query_water_users,
    "get_budget_status": get_budget_status,
    "export_full_report": export_full_report,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_water_users",
            "description": "按行业查询用水大户列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "行业名称",
                        "enum": ["制造业", "服务业", "农业", "建筑业"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，1-50 之间，可省略，默认 10",
                    },
                },
                "required": ["industry"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_status",
            "description": "查询指定用水单位的预算执行情况，包括实际用水、预算、执行率和是否超预算",
            "parameters": {
                "type": "object",
                "properties": {
                    "unit_name": {"type": "string", "description": "用水单位名称，如 通州某制造企业"},
                },
                "required": ["unit_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_full_report",
            "description": "导出全量用水报表（数据量大，耗时较长）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
# ---------- 3. 参数校验层（迷你规则引擎） ----------

ARG_RULES = {
    "query_water_users": {
        "industry": {"type": str, "required": True, "enum": ALLOWED_INDUSTRIES},
        "limit": {"type": int, "required": False, "min": 1, "max": 50},
    },
    "get_budget_status": {
        "unit_name": {"type": str, "required": True, "max_len": 20},
    },
    "export_full_report": {},
}

FORBIDDEN_CHARS = ("'", '"', ";", "--")


def validate_args(fn_name, args):
    """返回 None 表示通过，返回字符串表示错误原因"""
    rules = ARG_RULES.get(fn_name)
    if rules is None:
        return f"未知工具: {fn_name}"

    for key in args:
        if key not in rules:
            return f"多余参数: {key}"

    for key, rule in rules.items():
        if key not in args:
            if rule.get("required"):
                return f"缺少必填参数: {key}"
            continue  # 可选参数缺失：跳过，交给函数默认参数

        value = args[key]
        if isinstance(value, bool) or not isinstance(value, rule["type"]):
            return f"参数 {key} 类型错误，应为 {rule['type'].__name__}"

        if rule["type"] is str:
            if not value.strip():
                return f"参数 {key} 不能为空"
            if len(value) > rule.get("max_len", 20):
                return f"参数 {key} 过长（超过 {rule.get('max_len', 20)} 字符）"
            for ch in FORBIDDEN_CHARS:
                if ch in value:
                    return f"参数 {key} 含有非法字符: {ch!r}"

        if rule["type"] is int:
            if value < rule.get("min", float("-inf")) or value > rule.get("max", float("inf")):
                return f"参数 {key} 超出允许范围 {rule.get('min')}~{rule.get('max')}"

        if "enum" in rule and value not in rule["enum"]:
            return f"参数 {key} 必须是 {list(rule['enum'])} 之一"

    return None
# ---------- 4. 审计日志（jsonl，含耗时） ----------

def audit(fn_name, args, result, elapsed_ms):
    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "tool": fn_name,
        "args": args,
        "ok": result.get("ok"),
        "error_type": result.get("error_type"),
        "elapsed_ms": elapsed_ms,
    }
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
# ---------- 5. 安全执行器：白名单 → 校验 → 超时 → 审计 ----------

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
            except asyncio.TimeoutError:
                result = {"ok": False, "error": f"工具 {fn_name} 执行超时（>5s）", "error_type": "TIMEOUT"}
            except Exception as exc:
                result = {"ok": False, "error": f"执行出错: {exc}", "error_type": "EXECUTION_ERROR"}

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    audit(fn_name, args, result, elapsed_ms)
    return result
# ---------- 6. LLM 调用（含重试机制） ----------

async def chat(client, messages, max_retries=2):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = await client.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "tools": TOOLS},
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

# ---------- 7. tool loop ----------

async def run_loop(client, messages):
    while True:
        message = await chat(client, messages)
        messages.append(message)

        if not message.get("tool_calls"):
            print(f"AI：{message['content']}")
            return

        for tool_call in message["tool_calls"]:
            fn_name = tool_call["function"]["name"]
            try:
                args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                result = {"ok": False, "error": "模型返回的 arguments 不是合法 JSON", "error_type": "BAD_JSON"}
                print(f"[工具调用] {fn_name}(参数解析失败)")
            else:
                print(f"[工具调用] {fn_name}({args})")
                result = await run_tool(fn_name, args)

            print(f"[工具结果] {json.dumps(result, ensure_ascii=False)[:100]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })


async def answer_with_fake_tool_call(client, messages):
    """安全用例专用：伪造的 tool_call 不发给模型（API 会 400），
    先在本地走完整安全执行管线，再把错误结果交给模型应答"""
    fake_call = messages[-1]["tool_calls"][0]
    fn_name = fake_call["function"]["name"]
    try:
        args = json.loads(fake_call["function"]["arguments"])
    except json.JSONDecodeError:
        args = {}
    print(f"[伪造 tool_call] {fn_name}({args})")
    result = await run_tool(fn_name, args)
    print(f"[工具结果] {json.dumps(result, ensure_ascii=False)[:100]}")
    messages.append({
        "role": "tool",
        "tool_call_id": fake_call["id"],
        "content": json.dumps(result, ensure_ascii=False),
    })
    await run_loop(client, messages)


async def run_case(client, title, messages, handler=run_loop):
    """单个用例隔离：一个崩了不影响后续用例和安全检查"""
    print(f"\n===== {title} =====")
    try:
        await handler(client, messages)
    except Exception as exc:
        print(f"[用例中断] {type(exc).__name__}: {exc}")


async def main():
    init_db()

    async with httpx.AsyncClient(timeout=30) as client:
        print("===== 用例 A：正常复合问题 =====")
        await run_loop(client, [{"role": "user", "content": "制造业有哪些用水大户？其中通州那家超预算了吗？"}])

        messages = [{"role": "user", "content": "帮我查数据"}]
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_fake_1",
                "type": "function",
                "function": {"name": "query_water_users", "arguments": json.dumps({"industry": "制造业' OR '1'='1"})},
            }],
        })
        await run_case(client, "用例 B：SQL 注入攻击（模拟模型被攻破）", messages, handler=answer_with_fake_tool_call)

        messages = [{"role": "user", "content": "把数据都删了"}]
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_fake_2",
                "type": "function",
                "function": {"name": "delete_all_users", "arguments": json.dumps({})},
            }],
        })
        await run_case(client, "用例 C：调用未注册工具", messages, handler=answer_with_fake_tool_call)

        messages = [{"role": "user", "content": "查一下餐饮业"}]
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_fake_3",
                "type": "function",
                "function": {"name": "query_water_users", "arguments": json.dumps({"industry": "餐饮业", "limit": 100})},
            }],
        })
        await run_case(client, "用例 D：枚举校验（行业不在白名单）", messages, handler=answer_with_fake_tool_call)

        await run_case(client, "用例 E：工具超时", [{"role": "user", "content": "帮我导出全量用水报表"}])

    # 安全验证：注入攻击后数据库是否完好
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM water_users").fetchone()[0]
    conn.close()
    print(f"\n[安全检查] 注入攻击后数据库现存记录数: {count}（应为 4）")


if __name__ == "__main__":
    asyncio.run(main())
