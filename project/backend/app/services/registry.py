"""工具注册表：TOOLS 是给模型的 OpenAPI 描述，TOOL_FUNCTIONS 是名称到实现的映射。"""
from . import tools

TOOL_FUNCTIONS = {
    "query_water_users": tools.query_water_users,
    "get_budget_status": tools.get_budget_status,
    "find_nearby": tools.find_nearby,
    "get_street_ranking": tools.get_street_ranking,
    "export_full_report": tools.export_full_report,
    "inspect_water_budget": tools.inspect_water_budget,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_water_budget",
            "description": "一键巡查用水预算：检查指定区县/行业或全部单位，返回统计、执行比例、超额量和地图坐标。"
                           "结果先列超预算单位（按超额比例从高到低），再列接近上限、待核实、正常单位。"
                           "巡查结果会自动在地图着色；summary统计完整受检范围，data按status_filter筛选。"
                           "预算是用水额度；仅分析当前记录，不能做月度趋势或推断违法/污染。",
            "parameters": {
                "type": "object",
                "properties": {
                    "district": {"type": "string", "enum": ["大兴区", "朝阳区", "通州区", "顺义区"],
                                 "description": "可选，省略表示巡查全部区县，不要传‘全部’"},
                    "industry": {"type": "string", "enum": ["制造业", "服务业", "农业", "建筑业"],
                                 "description": "可选，省略表示巡查全部行业"},
                    "status_filter": {"type": "string", "enum": ["all", "over_budget", "attention"],
                                      "description": "默认all展示全部；要求标红仍用all。仅明确只看/只显示超预算时用over_budget；只看需关注的单位用attention"},
                    "warning_percent": {"type": "number", "minimum": 50, "maximum": 100,
                                        "description": "接近预算上限的百分比阈值，默认90；超过100%始终为超预算"},
                    "map_view": {"type": "string", "enum": ["overview", "priority"],
                                 "description": "默认overview展示巡查范围；用户要求定位重点或超额比例最高单位时用priority"},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_water_users",
            "description": "按行业查询用水大户列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                         "description": "行业名称，仅支持 enum 列出的 4 个值；"
                   "如果用户询问的行业不在其中（如“餐饮业”），"
                   "不要用其他行业代替，直接告知当前数据仅覆盖制造业、服务业、农业、建筑业",
                        "enum": ["制造业", "服务业", "农业", "建筑业"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，1-50 之间，可省略，默认 10",
                    },
                    "district": {
                        "type": "string",
                        "description": "区县名称，可选过滤条件，不传则查全部区县",
                        "enum": ["大兴区", "朝阳区", "通州区", "顺义区"],
                    },
                },
                "required": ["industry"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_status",
            "description": "查询单位预算执行情况。用户说‘它/这个单位’且地图已选中单位时可省略unit_name，服务端使用当前选中对象。不得编造名称。",
            "parameters": {
                "type": "object",
                "properties": {
                    "unit_name": {"type": "string", "description": "用水单位名称，如 通州某制造企业"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_full_report",
            "description": "生成真实的全量用水预算简报与CSV清单，返回可下载的文件内容",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearby",
            "description": "查询距离指定河流 distance_km 公里以内的用水大户，按距离由近到远排序",
            "parameters": {
                "type": "object",
                "properties": {
                    "river_name": {
                        "type": "string",
                        "description": "河流名称，当前数据仅收录潮白河；"
                                       "用户提到其他河流（如永定河）时如实告知未收录，不得用潮白河代替",
                        "enum": ["潮白河"],
                    },
                    "distance_km": {
                        "type": "number",
                        "description": "距离范围，单位公里，0.1-50 之间",
                    },
                },
                "required": ["river_name", "distance_km"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_street_ranking",
            "description": "按街道汇总用水量并排行（空间归属推导），回答“哪个街道用水量最大”类问题；仅含有用水大户的街道",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _tool(name, description, properties, required=()):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(required), "additionalProperties": False}}}


TOOL_FUNCTIONS.update({name: getattr(tools, name) for name in (
    "locate_water_unit", "set_map_layer", "filter_map_units", "reset_map_view",
    "analyze_selected_area", "generate_inspection_report",
)})
TOOLS.extend([
    _tool("locate_water_unit", "定位入库单位，返回真实坐标并驱动地图。省略名称时定位当前选中单位。需要地图页面。",
          {"unit_name": {"type": "string", "description": "真实单位名称；‘这个单位/它’且已有选中对象时省略"}}),
    _tool("set_map_layer", "显示/隐藏河道或用水单位图层。当前没有区县/街道边界图层，不得假装控制这些图层。",
          {"layer": {"type": "string", "enum": ["rivers", "water_users"]},
           "visibility": {"type": "string", "enum": ["show", "hide"]}}, ("layer", "visibility")),
    _tool("filter_map_units", "按状态筛选当前地图查询范围，保留当前区县/圈选范围；恢复全库使用reset_map_view。",
          {"status": {"type": "string", "enum": ["all", "over_budget", "near_limit", "normal", "invalid_data", "attention"]}}, ("status",)),
    _tool("reset_map_view", "恢复全库总览，清除圈选、单位选择及状态筛选，显示河道和全部用水单位。", {}),
    _tool("analyze_selected_area", "查询地图当前圈选多边形内的单位（包含边界），统计用水/预算并巡查异常。坐标由地图提供，不能猜测圈选范围。",
          {key: value for key, value in TOOLS[0]["function"]["parameters"]["properties"].items() if key != "district"}),
    _tool("generate_inspection_report", "根据数据库巡查结果生成Markdown简报和CSV清单供下载。默认last使用最近巡查范围；all是全库；area是当前圈选。支持显式区县/行业。返回的report含真实文件内容。",
          {"scope": {"type": "string", "enum": ["last", "all", "area"]},
           "district": {"type": "string", "enum": ["大兴区", "朝阳区", "通州区", "顺义区"]},
           "industry": {"type": "string", "enum": ["制造业", "服务业", "农业", "建筑业"]}}),
])

# Period-aware supervision tools retain old tool names for conversation compatibility.
_period_properties = {'year': {'type': 'integer', 'minimum': 2020, 'maximum': 2100, 'description': '统计年度；默认当前演示年度2026'},
                      'quarter': {'type': 'integer', 'minimum': 1, 'maximum': 4, 'description': '累计到第几季度末；默认3，样例仅有1至9月记录'}}
for _definition in TOOLS:
    _function = _definition['function']
    if _function['name'] in {'inspect_water_budget', 'analyze_selected_area', 'generate_inspection_report', 'get_budget_status'}:
        _function['parameters']['properties'].update(_period_properties)
    if _function['name'] == 'inspect_water_budget':
        _function['description'] = '按选定年度截至季度末执行监管巡查，返回已超年度指标、预计超年度指标、数据待核实和正常单位、证据及地图坐标。预计超用按已批复季节分配进度外推，不是已发生超用。已发生超指标严格超过20%标记监督检查建议（北京案例），不能认定违法。summary是完整范围，data按显示状态筛选。'
        _function['parameters']['properties']['warning_percent']['description'] = '仅兼容无周期原始快照；周期监管不使用固定90%规则'
    if _function['name'] == 'filter_map_units':
        _function['parameters']['properties']['status']['description'] = 'near_limit兼容代码表示预计超年度指标，over_budget表示已超年度指标，invalid_data表示数据待核实'
TOOL_FUNCTIONS.update({'get_unit_dossier': tools.get_unit_dossier, 'list_regulatory_cases': tools.list_regulatory_cases})
TOOLS.extend([
    _tool('get_unit_dossier', '查询单位档案、有效年度指标版本、水源用途、逐月计量、风险证据和预测方法。省略名称使用当前选中单位。',
          {'unit_name': {'type': 'string'}, **_period_properties}),
    _tool('list_regulatory_cases', '只读查询核查待办和办理历史，不能创建或变更行政处置，不得假称已派单或已办结。', {'unit_name': {'type': 'string'}}),
])

TOOL_FUNCTIONS.update({'get_report_draft': tools.get_report_draft, 'revise_inspection_report': tools.revise_inspection_report})
TOOLS.extend([
    _tool('get_report_draft', '读取当前选定报告的正文、可编辑字段、版本和已核实事实占位符，修改前先调用。', {}),
    _tool('revise_inspection_report', '按用户要求修改当前报告并保存新版本，不能只在回答里改写。使用完整替换字段，未传字段沿用旧稿。数字和日期只能引用facts占位符，如{{checked_count}}；不得手写数字。正文纯文本，可分段，标题纯文字。保留统计与数据口径，不能修改原始证据、编造原因或认定违法。',
          {'title': {'type': 'string', 'description': '报告标题，只用文字、空格或事实占位符，不含括号、冒号、Markdown标记等标点'},
           'overview': {'type': 'string', 'description': '汇总结论全文，数字用{{over_budget}}等服务端占位符'},
           'actions': {'type': 'string', 'description': '核查建议全文，可分段，不能编造已完成的处置'},
           'include_details': {'type': 'boolean', 'description': '是否附全部单位清单；精简版可关闭，CSV始终完整'},
           'include_evidence': {'type': 'boolean', 'description': '是否附逐单位风险证据；统计口径始终保留'}}),
])
for _definition in TOOLS:
    if _definition['function']['name'] == 'generate_inspection_report':
        _definition['function']['description'] += ' 同时持久保存报告V1，支持多轮修改及Word/PDF导出。用户调整已有稿件时使用revise_inspection_report，不能重新生成替代改稿。'
