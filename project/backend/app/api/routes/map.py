# app/api/routes/map.py（新文件）——普通 GET 端点，不进 registry（LLM 用不到它）
from fastapi import APIRouter, Query
from ...services.map_data import get_base_map, get_water_users
from ...schemas.map import AreaAnalysisRequest
from ...services.tools import inspect_area

router = APIRouter(tags=["map"])

@router.get("/map/base")
def base_map():
    return get_base_map()


@router.get("/map/water-users")
def water_users(year: int = Query(default=2026, ge=2020, le=2100), quarter: int = Query(default=3, ge=1, le=4)):
    return get_water_users(year, quarter)


@router.post("/map/area-analysis")
def area_analysis(request: AreaAnalysisRequest):
    return inspect_area(request.area.coordinates, request.industry, request.warning_percent, request.year, request.quarter)
