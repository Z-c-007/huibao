"""参数校验层（迷你规则引擎）：返回 None 表示通过，返回字符串表示错误原因。"""
import math

ALLOWED_INDUSTRIES = ("制造业", "服务业", "农业", "建筑业")
ALLOWED_DISTRICTS = ("大兴区", "朝阳区", "通州区", "顺义区")
ALLOWED_RIVERS = ("潮白河",)
FORBIDDEN_CHARS = ("'", '"', ";", "--")

ARG_RULES = {
    "inspect_water_budget": {
        "district": {"type": str, "required": False, "enum": ALLOWED_DISTRICTS},
        "industry": {"type": str, "required": False, "enum": ALLOWED_INDUSTRIES},
        "status_filter": {"type": str, "required": False, "enum": ("all", "over_budget", "attention")},
        "warning_percent": {"type": float, "required": False, "min": 50, "max": 100},
        "map_view": {"type": str, "required": False, "enum": ("overview", "priority")},
    },
    "query_water_users": {
        "industry": {"type": str, "required": True, "enum": ALLOWED_INDUSTRIES},
        "limit": {"type": int, "required": False, "min": 1, "max": 50},
        "district": {"type": str, "required": False, "enum": ALLOWED_DISTRICTS},
    },
    "get_budget_status": {
        "unit_name": {"type": str, "required": False, "max_len": 100},
    },
    "find_nearby": {
        "river_name": {"type": str, "required": True, "max_len": 20, "enum": ALLOWED_RIVERS},
        "distance_km": {"type": float, "required": True, "min": 0.1, "max": 50},
    },
    "get_street_ranking": {},
    "export_full_report": {},
}

ARG_RULES.update({
    "locate_water_unit": {"unit_name": {"type": str, "required": False, "max_len": 100}},
    "set_map_layer": {"layer": {"type": str, "required": True, "enum": ("rivers", "water_users")},
                      "visibility": {"type": str, "required": True, "enum": ("show", "hide")}},
    "filter_map_units": {"status": {"type": str, "required": True, "enum": ("all", "over_budget", "near_limit", "normal", "invalid_data", "attention")}},
    "reset_map_view": {},
    "analyze_selected_area": {key: rule for key, rule in ARG_RULES["inspect_water_budget"].items() if key != "district"},
    "generate_inspection_report": {"scope": {"type": str, "required": False, "enum": ("last", "all", "area")},
                                   "district": {"type": str, "required": False, "enum": ALLOWED_DISTRICTS},
                                   "industry": {"type": str, "required": False, "enum": ALLOWED_INDUSTRIES}},
})

_period_rules = {'year': {'type': int, 'required': False, 'min': 2020, 'max': 2100},
                 'quarter': {'type': int, 'required': False, 'min': 1, 'max': 4}}
for _name in ('inspect_water_budget', 'analyze_selected_area', 'generate_inspection_report', 'get_budget_status'):
    ARG_RULES[_name].update(_period_rules)
ARG_RULES['get_unit_dossier'] = {'unit_name': {'type': str, 'required': False, 'max_len': 100}, **_period_rules}
ARG_RULES['list_regulatory_cases'] = {'unit_name': {'type': str, 'required': False, 'max_len': 100}}
ARG_RULES['get_report_draft'] = {}
ARG_RULES['revise_inspection_report'] = {
    **{key: {'type': str, 'required': False, 'max_len': 100 if key == 'title' else 6000, 'prose': True} for key in ('title', 'overview', 'actions')},
    **{key: {'type': bool, 'required': False} for key in ('include_details', 'include_evidence')},
}


def validate_args(fn_name, args):
    rules = ARG_RULES.get(fn_name)
    if rules is None:
        return f"未知工具: {fn_name}"

    for key in args:
        if key not in rules:
            return f"多余参数: {key}"

    for key, rule in rules.items():
        if key not in args:
            if rule.get("required"):
                return f"缺少必填参数: {key}"
            continue  # 可选参数缺失：跳过，交给函数默认参数

        value = args[key]
        expected = rule["type"]
        if expected is float:
            # float 规则同时接受 int（模型可能传 5 表示 5.0 公里）；bool 是 int 子类，永远拒绝
            type_ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected is bool:
            type_ok = type(value) is bool
        else:
            type_ok = not isinstance(value, bool) and isinstance(value, expected)
        if not type_ok:
            return f"参数 {key} 类型错误，应为 {expected.__name__}"

        if rule["type"] is str:
            if not value.strip():
                return f"参数 {key} 不能为空"
            if len(value) > rule.get("max_len", 20):
                return f"参数 {key} 过长（超过 {rule.get('max_len', 20)} 字符）"
            for ch in (() if rule.get('prose') else FORBIDDEN_CHARS):
                if ch in value:
                    return f"参数 {key} 含有非法字符: {ch!r}"

        if rule["type"] in (int, float):
            if isinstance(value, float) and not math.isfinite(value):
                return f"参数 {key} 必须是有限数值"
            if value < rule.get("min", float("-inf")) or value > rule.get("max", float("inf")):
                return f"参数 {key} 超出允许范围 {rule.get('min')}~{rule.get('max')}"

        if "enum" in rule and value not in rule["enum"]:
            return f"参数 {key} 必须是 {list(rule['enum'])} 之一"

    return None
