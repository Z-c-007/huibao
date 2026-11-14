import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

SYSTEM_PROMPT = (
    "你是水预算智慧监管助手，专门回答北京市用水户相关问题。"
    "回答要简洁、专业，只回答水务监管相关内容。"
    "如果问题超出范围，请回答：'我主要负责水预算监管相关问题，请换个问法。'"
)

FEW_SHOT_EXAMPLES = [
    {"role": "user", "content": "通州某制造企业本月用水 12000 吨，预算 10000 吨，是否超预算？"},
    {"role": "assistant", "content": "该单位本月实际用水 12000 吨，预算 10000 吨，执行率为 120%，已超预算。"},
    {"role": "user", "content": "执行率怎么算？"},
    {"role": "assistant", "content": "执行率 = 实际用水量 / 预算量 × 100%。"},
]

SYSTEM_AND_EXAMPLES = [{"role": "system", "content": SYSTEM_PROMPT}] + FEW_SHOT_EXAMPLES


def build_messages(history, keep_last=4):
    kept_history = history[-keep_last * 2 :]
    return SYSTEM_AND_EXAMPLES + kept_history


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
        },
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return content, usage


async def main():
    history = []

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            user_input = input("你：")
            if user_input.lower() in ("exit", "quit", "退出"):
                break

            history.append({"role": "user", "content": user_input})

            messages = build_messages(history, keep_last=3)
            reply, usage = await chat(client, messages)

            history.append({"role": "assistant", "content": reply})

            print(f"AI：{reply}\n")
            print(
                f"[tokens: prompt={usage.get('prompt_tokens', '?')}, "
                f"completion={usage.get('completion_tokens', '?')}, "
                f"total={usage.get('total_tokens', '?')}]"
            )
            print(
                f"[已保留最近 {min(len(history) // 2, 3)} 轮对话 / "
                f"总历史 {len(history) // 2} 轮]\n"
            )


if __name__ == "__main__":
    asyncio.run(main())