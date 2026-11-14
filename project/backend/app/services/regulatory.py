"""Period-aware supervision rules. Forecasts and statutory inspection triggers differ."""
import calendar
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..core.config import DEMO_WATER_UNITS

PROFILE_FILE = Path(__file__).resolve().parents[2] / 'data/demo_regulatory_profiles.json'
POLICY_URL = 'https://www.beijing.gov.cn/zhengce/zhengcefagui/202310/t20231030_3290091.html'
FORECAST_METHOD = '按年度指标的演示季节分配进度外推：累计用水 ÷ 截至当期计划占比；假设后续用水结构保持一致。预测不是已发生超用。'
STATUS_LABELS = {'over_limit': '已超年度指标', 'forecast_risk': '预计超年度指标', 'data_pending': '数据待核实', 'normal': '执行正常'}
MAP_STATUS = {'over_limit': 'over_budget', 'forecast_risk': 'near_limit', 'data_pending': 'invalid_data', 'normal': 'normal'}


def profiles():
    if not DEMO_WATER_UNITS or not PROFILE_FILE.exists():
        return {}
    return {profile['name']: profile for profile in json.loads(PROFILE_FILE.read_text(encoding='utf-8'))}


def decimal(value):
    if isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def period(year=2026, quarter=3):
    if type(year) is not int or not 2020 <= year <= 2100 or type(quarter) is not int or not 1 <= quarter <= 4:
        raise ValueError('统计年度或季度无效')
    month = quarter * 3
    return dict(year=year, quarter=quarter, start=f'{year}-01-01',
                end=date(year, month, calendar.monthrange(year, month)[1]).isoformat(),
                label=f'{year}年度 · 截至第{quarter}季度末', comparison='本年累计用水 / 同年度有效指标', unit='立方米')


def evaluate_profile(unit, profile, year=2026, quarter=3):
    selected = period(year, quarter)
    issues, evidence = [], []
    indicator = profile.get('indicator', {}) if profile else {}
    annual = decimal(indicator.get('annual_volume'))
    if not profile:
        issues.append('未关联带周期的单位档案和计量记录，不能判定年度执行状态')
    elif indicator.get('year') != year:
        issues.append('未找到所选年度指标，不能用其他年度额度替代')
    if indicator.get('state') != 'issued':
        issues.append('指标尚未下达或不是有效版本')
    if annual is None or annual <= 0:
        issues.append('年度指标水量无效')
    if profile and (indicator.get('source') != profile.get('water_source') or indicator.get('purpose') != profile.get('purpose')):
        issues.append('指标水源或用途与档案不一致')
    if indicator.get('effective_from', '9999') > selected['start'] or indicator.get('effective_to', '') < selected['end']:
        issues.append('指标版本未覆盖完整统计期间，需要分段核算')
    permit = decimal(profile.get('permit_volume')) if profile else None
    if profile and profile.get('management_type') == '取水许可管理' and (not profile.get('permit_id') or permit is None or annual is not None and annual > permit):
        issues.append('取水许可信息缺失或指标超过许可水量')
    records = profile.get('monthly', []) if profile and indicator.get('year') == year else []
    rows = [record for record in records if type(record.get('month')) is int and 1 <= record['month'] <= quarter * 3]
    months = [record['month'] for record in rows]
    expected = set(range(1, quarter * 3 + 1))
    if set(months) != expected:
        issues.append('统计期间存在缺报月份或尚未到达该季度的数据截止日')
    if len(months) != len(set(months)):
        issues.append('计量月报重复，需核对后再汇总')
    for record in rows:
        volume = decimal(record.get('volume'))
        if volume is None or volume < 0 or record.get('quality') != 'verified':
            issues.append(f"{record['month']}月计量数据缺失或未经核实")
        if record.get('source') != indicator.get('source'):
            issues.append(f"{record['month']}月计量水源与指标不一致")
        if record.get('meter_id') not in {meter.get('id') for meter in profile.get('meters', [])}:
            issues.append(f"{record['month']}月计量表不属于当前单位档案")
    known = sum((decimal(row['volume']) for row in rows if decimal(row.get('volume')) is not None and decimal(row['volume']) >= 0), Decimal(0))
    used = known if not issues else None
    shares = [decimal(value) for value in indicator.get('monthly_shares', [])]
    valid_shares = len(shares) == 12 and all(value is not None and value > 0 for value in shares) and abs(sum(shares) - 1) < Decimal('.000001')
    progress = sum(shares[:quarter * 3]) if valid_shares else None
    rate = used / annual * 100 if used is not None and annual and annual > 0 else None
    forecast = used / progress if used is not None and progress else None
    if not issues and not valid_shares:
        evidence.append('缺少有效季节分配计划，不提供年度预测；已发生执行比例仍可核算')
    if issues:
        status = 'data_pending'
    elif used > annual:
        status = 'over_limit'
    elif not valid_shares and quarter < 4:
        status = 'data_pending'
        issues.append('缺少有效季节分配计划，不能判定预计全年是否超用')
    elif forecast is not None and forecast > annual:
        status = 'forecast_risk'
    else:
        status = 'normal'
    inspection_required = rate is not None and rate > 120
    if used is not None:
        evidence.append(f"{selected['start']}至{selected['end']}累计用水{used:,.2f}立方米；年度有效指标{annual:,.2f}立方米，版本{indicator.get('version')}。")
    if forecast is not None:
        evidence.append(f"截至当期计划占比{progress * 100:.0f}%，预计全年{forecast:,.2f}立方米。")
    if inspection_required:
        evidence.append('已发生年度超用严格超过20%，按北京管理办法第十二条建议进入监督检查；不是违法认定。')
    evidence.extend(dict.fromkeys(issues))
    return {**unit, 'water_used': float(known) if rows else None,
            'budget': float(annual) if annual is not None and indicator.get('year') == year and indicator.get('state') == 'issued' else None,
            'budget_status': MAP_STATUS[status], 'regulatory_status': status, 'status_label': STATUS_LABELS[status],
            'execution_rate': float(round(rate, 2)) if rate is not None else None,
            'over_budget_amount': float(max(used - annual, 0)) if used is not None else None,
            'over_budget_percent': float(round(max(rate - 100, 0), 4)) if rate is not None else None,
            'forecast_annual': float(round(forecast, 2)) if forecast is not None else None,
            'forecast_over_amount': float(round(max(forecast - annual, 0), 2)) if forecast is not None else None,
            'plan_progress_percent': float(progress * 100) if progress else None,
            'inspection_required': inspection_required, 'data_issues': list(dict.fromkeys(issues)), 'evidence': evidence,
            'indicator_version': indicator.get('version'), 'indicator_state': indicator.get('state', 'unknown'),
            'water_source': profile.get('water_source') if profile else None, 'purpose': profile.get('purpose') if profile else None,
            'period': selected, 'forecast_method': FORECAST_METHOD if forecast is not None else None,
            'policy_basis': {'region': '北京案例', 'article': '第十二条', 'url': POLICY_URL},
            'data_origin': '人工演示档案与月度计量样例' if profile and profile.get('demo') else '缺少可核验周期档案'}


def decorate_units(units, year=2026, quarter=3, require_profiles=False):
    catalog = profiles()
    return [evaluate_profile(unit, catalog.get(unit['name']), year, quarter)
            if require_profiles or unit['name'] in catalog else unit for unit in units]


def regulatory_inventory(year=2026, quarter=3, district=None, industry=None):
    from .db import get_db
    from .budget_data import read_water_units, build_inspection
    with get_db() as conn:
        units = read_water_units(conn, district=district, industry=industry, year=year, quarter=quarter, require_profiles=True)
    return build_inspection(units, district=district, industry=industry, year=year, quarter=quarter)


def unit_dossier(unit_name, year=2026, quarter=3):
    from .db import get_db
    from .budget_data import read_water_units
    with get_db() as conn:
        units = read_water_units(conn, unit_name=unit_name, year=year, quarter=quarter, require_profiles=True)
    if not units:
        return {'ok': False, 'error': '未找到单位', 'error_type': 'NOT_FOUND'}
    archive = profiles().get(unit_name)
    return {'ok': True, 'data': units[0], 'archive': archive, 'period': period(year, quarter),
            'note': '档案和计量为明确标注的演示数据；未接入行业定额，不作水效合规结论。'}
