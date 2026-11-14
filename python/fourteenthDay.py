"""Day 14：LangChain 最小 chat，与手写 llm.py 逐字段对照。

对照基准：backend/app/services/llm.py（httpx 手拼 /chat/completions）
官方依据：
- https://docs.langchain.com/oss/python/langchain/install
- https://python.langchain.com/docs/integrations/chat/deepseek/
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

# Windows 控制台 GBK，中文日志会 UnicodeEncodeError——与手写 llm.py 同款处理
sys.stdout.reconfigure(encoding="utf-8")

# 复用 Day 4 起的 .env 约定（LLM_API_KEY / LLM_BASE_URL / LLM_MODEL），不新造 DEEPSEEK_API_KEY
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
LLM_API_KEY = os.environ["LLM_API_KEY"]
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# 官方文档实例化四参数：model / temperature / max_tokens / timeout / max_retries
# api_key、api_base 显式传入以对接现有 .env；LLM_BASE_URL 手写版拼在 /chat/completions 前，
# openai SDK（框架底层）同样在 base_url 后拼路径，所以直接传 https://api.deepseek.com 等价
llm = ChatDeepSeek(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    api_base=LLM_BASE_URL,   # 若此处报 pydantic 校验错误，改用 openai_api_base=...（同一字段的原始名）
    temperature=0,
    max_retries=2,           # 手写 chat() 的 max_retries=2 循环，框架里是一个构造参数
)

# 手写: messages=[{"role": "system", "content": ...}, {"role": "user", ...}]
# 框架: 元组形式 (role, content)，invoke 时内部转换
ai_msg = llm.invoke([
    ("system", "你是水利监管助手，只用工具返回的数据回答，不编造。"),
    ("human", "你是谁？用一句话回答。"),
])

# ===== 逐字段对照手写 resp.json() 结构 =====
print("content:", ai_msg.content)                        # 手写: choices[0].message.content
print("usage:", ai_msg.usage_metadata)                   # 手写: usage
print("finish_reason:", ai_msg.response_metadata.get("finish_reason"))  # 手写: choices[0].finish_reason
print("model:", ai_msg.response_metadata.get("model_name"))