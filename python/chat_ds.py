import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")


async def chat(client, user_input):
    resp = await client.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": user_input}],
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            user_input = input("你说：")
            if user_input.lower() in ("exit", "quit", "退出"):
                break
            reply = await chat(client, user_input)
            print(f"AI：{reply}\n")


if __name__ == "__main__":
    asyncio.run(main())