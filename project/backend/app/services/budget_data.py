"""Read-only unit inventory and deterministic budget rules shared by map and agent."""
from decimal import Decimal, InvalidOperation
import json
from datetime import datetime, timedelta, timezone

from .spatial import validate_ring
from ..core.config import DEMO_WATER_UNITS


def _number(value):
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def evaluate_budget(water_used, budget_value, warning_percent=90):
    used, budget = _number(water_used), _number(budget_value)
    valid = used is not None and budget is not None and used >= 0 and budget > 0
    rate = used / budget * 100 if valid else None
    # Compare unrounded values, so 100.004% remains over budget.
    status = ("invalid_data" if not valid else "over_budget" if rate > 100
              else "near_limit" if rate >= Decimal(str(warning_percent)) else "normal")
    labels = {"invalid_data": "待核实", "over_budget": "超预算",
              "near_limit": "接近上限", "normal": "正常"}
    return {
        "water_used": float(used) if used is not None else None,
        "budget": float(budget) if budget is not None else None,
        "budget_status": status, "status_label": labels[status],
        "execution_rate": float(round(rate, 2)) if valid else None,
        "over_budget_amount": float(max(used - budget, Decimal(0))) if valid else None,
        "over_budget_percent": float(round(max(rate - 100, Decimal(0)), 4)) if valid else None,
    }


def classify_unit(row, warning_percent=90):
    return {
        "id": row[0], "name": row[1], "industry": row[2],
        **evaluate_budget(row[3], row[4], warning_percent),
        "lon": float(row[5]), "lat": float(row[6]),
        "district": row[7] or "未归属", "street": row[8] or "未归属",
    }


def read_water_units(conn, district=None, industry=None, warning_percent=90, area=None, unit_name=None, year=2026, quarter=3, require_profiles=False):
    # LATERAL selects a single spatial membership even for touching/overlapping
    # boundaries, avoiding duplicated units/counts. All user filters are parameters.
    sql = """
        SELECT u.id, u.name, u.industry, u.water_used, u.budget,
               ST_X(u.geom), ST_Y(u.geom), d.name, s.name
        FROM water_users u
        LEFT JOIN LATERAL (
            SELECT name FROM districts WHERE ST_Covers(geom, u.geom)
            ORDER BY id LIMIT 1
        ) d ON TRUE
        LEFT JOIN LATERAL (
            SELECT name FROM streets WHERE ST_Covers(geom, u.geom)
            ORDER BY id LIMIT 1
        ) s ON TRUE
        WHERE TRUE
    """
    params = []
    if district is not None:
        sql += " AND d.name = %s"
        params.append(district)
    if industry is not None:
        sql += " AND u.industry = %s"
        params.append(industry)
    if unit_name is not None:
        sql += " AND u.name = %s"
        params.append(unit_name)
    if area is not None:
        ring = validate_ring(area)
        sql += " AND ST_Covers(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), u.geom)"
        params.append(json.dumps({"type": "Polygon", "coordinates": [ring]}))
    sql += " ORDER BY u.id"
    from .regulatory import decorate_units
    units = [classify_unit(row, warning_percent) for row in conn.execute(sql, params).fetchall()]
    return decorate_units(units, year, quarter, require_profiles)


def build_inspection(units, district=None, industry=None, status_filter="all", warning_percent=90, map_view="overview", area=None, year=None, quarter=3):
    from .regulatory import period, FORECAST_METHOD, POLICY_URL
    selected = period(year, quarter) if year is not None else next((unit['period'] for unit in units if 'period' in unit), None)
    priority = {"over_budget": 0, "near_limit": 1, "invalid_data": 2, "normal": 3}
    def sort_key(unit):
        used, budget = _number(unit["water_used"]), _number(unit["budget"])
        exact_rate = used / budget if used is not None and budget is not None and budget > 0 else Decimal(0)
        return priority[unit["budget_status"]], not unit.get('inspection_required', False), -exact_rate, unit["name"]

    ordered = sorted(units, key=sort_key)
    visible = [unit for unit in ordered if (
        status_filter == "all"
        or status_filter == "over_budget" and unit["budget_status"] == "over_budget"
        or status_filter == "attention" and unit["budget_status"] != "normal"
    )]
    counts = {status: sum(unit["budget_status"] == status for unit in units) for status in priority}
    pending_reasons = {'indicator_pending': 0, 'missing_monthly': 0, 'other': 0}
    for unit in units:
        if unit.get('regulatory_status') != 'data_pending':
            continue
        reason = ('indicator_pending' if unit.get('indicator_state') == 'pending' else
                  'missing_monthly' if any('缺报' in issue or '计量数据缺失' in issue for issue in unit.get('data_issues', [])) else 'other')
        pending_reasons[reason] += 1
    verified_units = [unit for unit in units if not selected or unit.get('regulatory_status') != 'data_pending']
    total_used = sum(Decimal(str(unit["water_used"])) for unit in verified_units if unit["water_used"] is not None and unit["water_used"] >= 0)
    total_budget = sum(Decimal(str(unit["budget"])) for unit in verified_units if unit["budget"] is not None and unit["budget"] >= 0)
    return {
        "ok": True,
        "demo_mode": DEMO_WATER_UNITS,
        "period": selected,
        "rule_mode": "period_supervision" if selected else "snapshot",
        "forecast_method": FORECAST_METHOD if selected else None,
        "policy_basis": {"region": "北京案例", "url": POLICY_URL, "inspection_trigger": "已发生年度超指标严格超过20%"} if selected else None,
        "scope": {"district": district or "全部区县", "industry": industry or "全部行业", **({"area": "地图圈选区域"} if area else {})},
        "thresholds": {"near_limit_percent": warning_percent, "over_budget_percent": 100, "inspection_execution_percent": 120},
        "summary": {
            "checked_count": len(units), "displayed_count": len(visible), **counts,
            "forecast_risk": sum(unit.get('regulatory_status') == 'forecast_risk' for unit in units),
            "inspection_required": sum(unit.get('inspection_required', False) for unit in units),
            "data_pending_reasons": pending_reasons,
            "total_water_used": float(total_used), "total_budget": float(total_budget),
            "totals_complete": counts["invalid_data"] == 0,
            "aggregate_execution_rate": float(round(total_used / total_budget * 100, 2)) if total_budget > 0 and not counts["invalid_data"] else None,
            "total_over_budget_amount": float(sum(
                Decimal(str(unit["over_budget_amount"] or 0)) for unit in units
            )),
        },
        "status_filter": status_filter, "map_view": map_view, "data": visible, "all_units": ordered,
        "area": {"type": "Polygon", "coordinates": [validate_ring(area)]} if area else None,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "note": ("演示模式：单位档案、指标及计量为人工样例，不是实际企业监管结论。" if DEMO_WATER_UNITS else "") + (f"{selected['label']}，已发生水量与同年度有效指标比较；预计超用是季节进度外推，不是既成超用或违法认定。" if selected else "仅为未标注周期的原始记录快照，不能判定年度风险。") + "区县、街道依据当前库中的空间数据；指标未下达或月报缺失须先核实。",
    }
