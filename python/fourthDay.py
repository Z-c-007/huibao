import asyncio
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
load_dotenv()
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
SYSTEM_PROMPT = (
    "你是水预算监管系统的信息抽取助手。"
    "从用户的自然语言描述中抽取：行业、实际用水量、预算量。"
    "必须只输出一个 JSON 对象，不要输出任何解释。"
    '格式：{"industry": "行业名称", "water_used": 数字, "budget": 数字}'
)
async def extract_one(client, text):
    resp = await client.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
        },
    )
    raw = resp.text
    try:
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e} | 原始响应: {raw[:200]}"
async def main():
    text = Path("data/water_users.txt").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]

    async with httpx.AsyncClient(timeout=30) as client:
        for i, line in enumerate(lines, start=1):
            result, err = await extract_one(client, line)
            if err:
                print(f"[失败] 第{i}行: {err}")
            else:
                print(f"[成功] 第{i}行: {json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    asyncio.run(main())