"""工具实现层：SQL 固定写死，模型只能填参数值。"""
from copy import deepcopy

from .db import get_db
from .budget_data import read_water_units, build_inspection, evaluate_budget
from .agent_context import get_context
from .inspection_reports import create_report


def query_water_users(industry, limit=10, district=None):
    """按行业查询用水大户；district 可选，按区县过滤（归属由 ST_Within 空间推导，非外键）"""
    conn = get_db()
    try:
        sql = (
            "SELECT u.name, u.industry, u.water_used, u.budget "
            "FROM water_users u "
            "JOIN districts d ON ST_Within(u.geom, d.geom) "
            "WHERE u.industry = %s "
        )
        params = [industry]
        if district is not None:
            sql += "AND d.name = %s "
            params.append(district)
        sql += "ORDER BY u.water_used DESC LIMIT %s"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return {
            "ok": True,
            "data": [
                {"name": r[0], "industry": r[1],
                 "water_used": int(r[2]), "budget": int(r[3])}
                for r in rows
            ],
        }
    finally:
        conn.close()


def get_budget_status(unit_name=None, year=None, quarter=None):
    """查询指定用水单位的预算执行情况"""
    unit_name = unit_name or get_context().selected_unit
    if not unit_name:
        return {"ok": False, "error": "请先在地图选中单位，或提供明确的单位名称。", "error_type": "NOT_SELECTED"}
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT water_used, budget FROM water_users WHERE name = %s",
            (unit_name,),
        ).fetchone()
        if row is None:
            return {"ok": False, "error": f"未找到单位: {unit_name}", "error_type": "NOT_FOUND"}
        details = evaluate_budget(row[0], row[1])
        from .regulatory import profiles
        if unit_name in profiles():
            details = read_water_units(conn, unit_name=unit_name, year=year or get_context().year, quarter=quarter or get_context().quarter)[0]
        else:
            details['period'] = None
            details['note'] = '无周期原始记录快照，不能作为年度超指标或预计超用结论。'
        return {
            "ok": True,
            "data": {
                "unit": unit_name,
                **details,
                "rate": round(details["execution_rate"] / 100, 2) if details["execution_rate"] is not None else None,
                "status": details["status_label"] if 'regulatory_status' in details else "已超预算" if details["budget_status"] == "over_budget" else details["status_label"],
            },
        }
    finally:
        conn.close()


def find_nearby(river_name, distance_km):
    """查询距指定河流 distance_km 公里以内的用水大户（每户取最近河段距离，由近到远）"""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT u.name, u.industry, u.water_used, u.budget,
                   ROUND((MIN(ST_Distance(u.geom::geography, r.geom::geography)) / 1000.0)::numeric, 2)
                       AS distance_km,
                   ST_X(u.geom) AS lon,
                   ST_Y(u.geom) AS lat
            FROM water_users u
            JOIN rivers r
              ON ST_DWithin(u.geom::geography, r.geom::geography, %s)
             AND r.name = %s
            GROUP BY u.id, u.name, u.industry, u.water_used, u.budget
            ORDER BY distance_km
            """,
            (distance_km * 1000, river_name),
        ).fetchall()
        return {
            "ok": True,
            "data": [
                {"name": r[0], "industry": r[1],
                 "water_used": int(r[2]), "budget": int(r[3]),
                 "distance_km": float(r[4]),
                 "lon": float(r[5]), "lat": float(r[6])}
                for r in rows
            ],
        }
    finally:
        conn.close()


def get_street_ranking():
    """按街道汇总用水量排行（ST_Within 空间归属，仅含有用水大户的街道）"""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT s.name AS street, d.name AS district,
                   SUM(u.water_used) AS total_used, COUNT(*) AS user_count
            FROM streets s
            JOIN districts d ON s.district_id = d.id
            JOIN water_users u ON ST_Within(u.geom, s.geom)
            GROUP BY s.name, d.name
            ORDER BY total_used DESC
            """,
        ).fetchall()
        return {
            "ok": True,
            "data": [
                {"street": r[0], "district": r[1],
                 "total_used": int(r[2]), "user_count": int(r[3])}
                for r in rows
            ],
        }
    finally:
        conn.close()


def export_full_report():
    """Legacy name now produces real full-scope Markdown/CSV artifacts."""
    return generate_inspection_report(scope="all")


def inspect_water_budget(district=None, industry=None, status_filter="all", warning_percent=90, map_view="overview", year=None, quarter=None):
    """Inspect every unit in the requested scope, calculate priorities and return map locations."""
    return _inspect_scope(district, industry, status_filter, warning_percent, map_view, year=year, quarter=quarter)


def _inspect_scope(district=None, industry=None, status_filter="all", warning_percent=90, map_view="overview", area=None, year=None, quarter=None):
    year, quarter = year or get_context().year, quarter or get_context().quarter
    conn = get_db()
    try:
        units = read_water_units(conn, district, industry, warning_percent, area=area, year=year, quarter=quarter, require_profiles=True)
        return build_inspection(units, district, industry, status_filter, warning_percent, map_view, area=area, year=year, quarter=quarter)
    finally:
        conn.close()


def _map_error():
    return {"ok": False, "error": "请在地图一张图页面使用地图操作。", "error_type": "MAP_UNAVAILABLE"}


def locate_water_unit(unit_name=None):
    context = get_context()
    if not context.map_available:
        return _map_error()
    name = unit_name or context.selected_unit
    if not name:
        return {"ok": False, "error": "请先选中单位，或提供单位名称。", "error_type": "NOT_SELECTED"}
    conn = get_db()
    try:
        units = read_water_units(conn, unit_name=name, year=context.year, quarter=context.quarter)
    finally:
        conn.close()
    if not units:
        return {"ok": False, "error": f"未找到单位：{name}", "error_type": "NOT_FOUND"}
    return {"ok": True, "action": "locate_unit", "data": units,
            "message": "地图定位指令已生成，坐标来自当前入库记录。"}


def set_map_layer(layer, visibility):
    if not get_context().map_available:
        return _map_error()
    return {"ok": True, "action": "set_layer", "layer": layer, "visibility": visibility}


def filter_map_units(status):
    if not get_context().map_available:
        return _map_error()
    return {"ok": True, "action": "filter_units", "status": status,
            "note": "筛选当前地图查询范围内的单位；恢复全库请使用reset_map_view。"}


def reset_map_view():
    if not get_context().map_available:
        return _map_error()
    return {"ok": True, "action": "reset_map"}


def analyze_selected_area(industry=None, status_filter="all", warning_percent=90, map_view="overview", year=None, quarter=None):
    context = get_context()
    if not context.map_available:
        return _map_error()
    if context.area is None:
        return {"ok": False, "error": "请先在地图圈选一个区域。", "error_type": "AREA_NOT_SELECTED"}
    return _inspect_scope(industry=industry, status_filter=status_filter, warning_percent=warning_percent,
                          map_view=map_view, area=context.area, year=year, quarter=quarter)


def inspect_area(area, industry=None, warning_percent=90, year=None, quarter=None):
    """Direct map API uses the same spatial/budget path as the agent."""
    return _inspect_scope(industry=industry, warning_percent=warning_percent, area=area, year=year, quarter=quarter)


def generate_inspection_report(scope="last", district=None, industry=None, year=None, quarter=None):
    context = get_context()
    if scope == "last" and district is None and industry is None and year is None and quarter is None and context.latest_report:
        report = deepcopy(context.latest_report)
        report.pop("report", None)
    else:
        if scope == "area":
            if not context.map_available:
                return _map_error()
            if context.area is None:
                return {"ok": False, "error": "请先圈选区域。", "error_type": "AREA_NOT_SELECTED"}
            params = {"district": district, "industry": industry, "area": context.area}
        elif scope == "all" or district is not None or industry is not None:
            params = {"district": district, "industry": industry}
        elif context.previous_scope:
            params = context.previous_scope
        else:
            return {"ok": False, "error": "请先执行巡查，或明确生成全量简报。", "error_type": "NO_INSPECTION"}
        if year is not None: params['year'] = year
        if quarter is not None: params['quarter'] = quarter
        report = _inspect_scope(**params)
    if not report.get('ok'):
        return report
    from .report_drafts import create_draft
    report["report"] = create_draft(report)
    context.report_draft = report['report']
    return report


def get_unit_dossier(unit_name=None, year=None, quarter=None):
    from .regulatory import unit_dossier
    name = unit_name or get_context().selected_unit
    if not name:
        return {'ok': False, 'error': '请提供单位名称或先在地图选中单位', 'error_type': 'NOT_SELECTED'}
    return unit_dossier(name, year or get_context().year, quarter or get_context().quarter)


def list_regulatory_cases(unit_name=None):
    from .regulatory_cases import list_cases
    return {'ok': True, 'data': list_cases(unit_name)}


def get_report_draft():
    draft = get_context().report_draft
    if not draft:
        return {'ok': False, 'error': '请先生成报告或选择已保存报告', 'error_type': 'NO_REPORT'}
    return {'ok': True, 'report': draft}


def revise_inspection_report(title=None, overview=None, actions=None, include_details=None, include_evidence=None):
    from .report_drafts import revise_draft
    context = get_context()
    if not context.report_draft:
        return get_report_draft()
    previous = context.report_draft
    changes = {key: value for key, value in locals().copy().items() if key in ('title', 'overview', 'actions', 'include_details', 'include_evidence') and value is not None}
    if not changes:
        return {'ok': False, 'error': '请至少修改一个报告字段', 'error_type': 'NO_CHANGES'}
    draft = revise_draft(previous['report_id'], previous['version'], previous['latest_version'], changes, context.report_instruction)
    context.report_draft = draft
    return {'ok': True, 'report': draft}
