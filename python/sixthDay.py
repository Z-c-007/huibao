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
    }
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
    user_input = "制造业有哪些用水大户？"
    messages = [{"role": "user", "content": user_input}]

    async with httpx.AsyncClient(timeout=30) as client:
        message = await chat(client, messages)
        messages.append(message)

        if message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            fn_name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])

            if fn_name == "query_water_users":
                result = query_water_users(**args)
            else:
                result = {"error": f"未知工具: {fn_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })

            final = await chat(client, messages)
            print(f"AI：{final['content']}")
        else:
            print(f"AI：{message['content']}")


if __name__ == "__main__":
    asyncio.run(main())