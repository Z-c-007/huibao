"""ChatRequest / ChatResponse / ToolResult：Pydantic 请求与响应模型（类比前端 TS interface）"""
from pydantic import BaseModel, Field
from .map import MapContext


class ReportContext(BaseModel):
    report_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    version: int = Field(ge=1, strict=True)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    thinking: bool = True
    map_context: MapContext | None = None
    report_context: ReportContext | None = None


class ToolResult(BaseModel):
    tool: str
    args: dict
    result: dict


class ChatResponse(BaseModel):
    answer: str
    tool_results: list[ToolResult] = []
