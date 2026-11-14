"""Day 14：@tool 自动生成 schema，与手写 registry.py 的 TOOLS 逐字段对照。

对照基准：backend/app/services/registry.py（手写 OpenAPI function dict）
官方依据：https://docs.langchain.com/oss/python/langchain/tools
- docstring → description；类型注解 → schema；args_schema=Pydantic 复刻 enum/required
"""
import json
import sys
from typing import Literal

from langchain.tools import tool
from pydantic import BaseModel, Field

sys.stdout.reconfigure(encoding="utf-8")

# ===== 手写 TOOLS[3] find_nearby 的等价物 =====
class FindNearbyInput(BaseModel):
    river_name: Literal["潮白河"] = Field(
        description="河流名称，当前数据仅收录潮白河；"
                    "用户提到其他河流（如永定河）时如实告知未收录，不得用潮白河代替",
    )
    distance_km: float = Field(
        description="距离范围，单位公里，0.1-50 之间",
    )

# ===== 手写 TOOLS[0] query_water_users 的等价物（含可选参数+默认值） =====
class QueryWaterUsersInput(BaseModel):
    industry: Literal["制造业", "服务业", "农业", "建筑业"] = Field(
        description="行业名称，仅支持 enum 列出的 4 个值；"
                    "如果用户询问的行业不在其中（如“餐饮业”），"
                    "不要用其他行业代替，直接告知当前数据仅覆盖制造业、服务业、农业、建筑业",
    )
    limit: int = Field(default=10, description="返回条数上限，1-50 之间，可省略，默认 10")
    district: Literal["大兴区", "朝阳区", "通州区", "顺义区"] | None = Field(
        default=None,
        description="区县名称，可选过滤条件，不传则查全部区县",
    )

# 函数体是占位：真 SQL 在 backend/app/services/tools.py，Day 15 才接。
# 今天的验收对象是 schema 自动生成，不是 SQL 执行。
@tool(args_schema=FindNearbyInput)
def find_nearby(river_name: str, distance_km: float) -> dict:
    """查询距离指定河流 distance_km 公里以内的用水大户，按距离由近到远排序"""
    return {"ok": False, "error": "Day 15 接入真库"}

@tool(args_schema=QueryWaterUsersInput)
def query_water_users(industry: str, limit: int = 10, district: str | None = None) -> dict:
    """按行业查询用水大户列表"""
    return {"ok": False, "error": "Day 15 接入真库"}

# ===== 与手写 TOOLS 对应条目并排对照 =====
# name      ← 手写 function.name（默认取函数名，snake_case）
# description ← 手写 function.description（来自 docstring）
# args      ← 手写 function.parameters（由 args_schema 自动生成）
for t in (find_nearby, query_water_users):
    print("=" * 60)
    print("name:", t.name)
    print("description:", t.description)
    print("args schema:")
    print(json.dumps(t.args, ensure_ascii=False, indent=2))