import asyncio
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

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
                        "description": "行业名称，如 制造业、餐饮业",
                    }
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
                    "unit_name": {
                        "type": "string",
                        "description": "用水单位名称，如 通州某制造企业",
                    }
                },
                "required": ["unit_name"],
            },
        },
    },
]


def query_water_users(industry):
    mock_data = {
        "制造业": [
            {"name": "通州某制造企业", "water_used": 12000, "budget": 10000},
            {"name": "大兴某制造企业", "water_used": 15000, "budget": 20000},
        ],
        "餐饮业": [
            {"name": "朝阳某餐饮企业", "water_used": 3000, "budget": 4000},
        ],
    }
    return mock_data.get(industry, [])


def get_budget_status(unit_name):
    mock_data = {
        "通州某制造企业": {"unit": "通州某制造企业", "water_used": 12000, "budget": 10000, "rate": 1.2, "status": "已超预算"},
        "大兴某制造企业": {"unit": "大兴某制造企业", "water_used": 15000, "budget": 20000, "rate": 0.75, "status": "正常"},
        "朝阳某餐饮企业": {"unit": "朝阳某餐饮企业", "water_used": 3000, "budget": 4000, "rate": 0.75, "status": "正常"},
    }
    return mock_data.get(unit_name, {"error": f"未找到单位: {unit_name}"})


TOOL_FUNCTIONS = {
    "query_water_users": query_water_users,
    "get_budget_status": get_budget_status,
}


async def chat(client, messages):
    resp = await client.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


async def main():
    user_input = "制造业有哪些用水大户？其中通州那家超预算了吗？"
    messages = [{"role": "user", "content": user_input}]

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            message = await chat(client, messages)
            messages.append(message)

            if not message.get("tool_calls"):
                print(f"AI：{message['content']}")
                break

            for tool_call in message["tool_calls"]:
                fn_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                print(f"[工具调用] {fn_name}({args})")

                fn = TOOL_FUNCTIONS.get(fn_name)
                if fn is None:
                    result = {"error": f"未知工具: {fn_name}"}
                else:
                    result = fn(**args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })


if __name__ == "__main__":
    asyncio.run(main())