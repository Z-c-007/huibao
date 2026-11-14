"""tool loop：编排循环，最终返回 (answer, tool_results)。"""
import json

from .executor import run_tool
from .llm import chat, stream_chat
from .agent_context import bind_context, context_prompt

# Deterministic tool evidence and selected reporting period govern every conclusion.
SYSTEM_PROMPT = (
    "你是水利预算监管助手，面向水务局和节水中心监管人员。"
    "必须通过工具查证数据，引用工具数字和证据，不得编造单位、原因或操作结果。"
    "标注演示的档案、指标和计量为人工样例，不能当作真实企业监管结论。"
    "默认演示年度2026，截至第三季度末，有1至9月记录；不能声称其他年度或第四季度已完整入库。"
    "用户指定年度和季度时传year/quarter，未指定时遵循当前上下文。季度表示本年累计到该季度末，与同年度有效指标比较。"
    "预算巡查使用inspect_water_budget；分析当前圈选范围用analyze_selected_area，坐标由上下文给出，不可猜测。"
    "按照period、regulatory_status、evidence、data_issues作答：over_limit是已超年度指标，forecast_risk是预计超年度指标，data_pending是数据待核实。"
    "地图兼容代码over_budget、near_limit、invalid_data分别对应这三类；near_limit不代表固定90%阈值。"
    "预测采用演示季节分配进度外推，须说明假设，不可认定为已经超用、处罚依据或违法。"
    "inspection_required是北京案例已发生年度超指标严格超过20%的监督检查建议；超过100%不自动代表违法。"
    "未下达指标、缺报、不同周期或水源用途不一致时先说明需核实什么，不能以部分数据计算完整执行比例。"
    "数据待核实的主要原因数量读取summary.data_pending_reasons，不能把所有待核实单位都称为缺报；单位可能有多个问题，分类统计优先列指标未下达。"
    "无period的数据只是原始快照，不能声称是年度执行或某月趋势；未接入行业定额与真实产量，不能作水效达标结论。"
    "查询档案、指标版本、水表、月度计量和风险证据用get_unit_dossier；单个单位执行用get_budget_status。"
    "‘这个单位/它’指上下文选中单位，未选中时要求明确名称；异常原因只能提出待核实假设，不能仅凭比例断言漏水。"
    "查询办理进度、整改历史、核查待办用list_regulatory_cases；创建和状态流转由用户在监管工作台填写。"
    "没有行政审批、派单、处罚或自动办结工具，不得假称已执行这些动作。"
    "按行业查询用query_water_users，街道用水排行用get_street_ranking，河流附近用find_nearby；仅支持工具白名单范围，河流仅潮白河，不得擅自替代。"
    "地图操作须调用locate_water_unit/set_map_layer/filter_map_units/reset_map_view；只改变显示使用filter_map_units以保留范围，回全库使用reset_map_view。"
    "巡查标红仍传status_filter=all；明确只显示已超指标时用over_budget；只看需关注用attention。"
    "巡查默认map_view=overview，明确定位重点对象时才用priority；结果先监督检查对象，再其他超用、预测风险、数据待核实与正常单位。"
    "生成报告用generate_inspection_report：刚才范围scope=last，全库all，圈选area；报告返回文件供用户点击，不是已保存到磁盘。"
    "已有报告的精简、重写、改标题、突出重点、调整清单证据等要求，先调用get_report_draft，再调用revise_inspection_report保存新版，不能只口头给出改稿，也不能重新巡查覆盖快照。"
    "报告可编辑overview/actions/title，include_details和include_evidence控制附件篇幅。数字、日期和比例仅用facts内{{字段名}}占位符；不要手写数字或中文数字代替统计。建议是拟采取的动作，不得编造原因、办理结果或负责人承诺。"
    "修改工具失败需修正参数后重试，成功时说明新版本和修改重点，Word/PDF由报告卡片下载。用户明确要求重新取数才生成新报告。"
    "最终答复简明说明统计期间、水量单位、已超/预计超/数据待核实数量、依据及下一步核查建议。"
    "使用中文业务状态名称，不必输出内部状态代码或字段名称。"
)


async def _run_loop(client, messages):
    tool_results = []
    # 确保系统提示词永远在对话最前面（history 来自前端时也统一注入）
    if not messages or messages[0].get("role") != "system":
        messages = [{"role": "system", "content": SYSTEM_PROMPT + context_prompt()}] + messages

    while True:
        message = await chat(client, messages)
        messages.append(message)

        if not message.get("tool_calls"):
            # 模型最终回答：不再 print，而是返回给上层（API 路由）
            return message["content"], tool_results

        for tool_call in message["tool_calls"]:
            fn_name = tool_call["function"]["name"]
            try:
                args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}
                result = {"ok": False, "error": "模型返回的 arguments 不是合法 JSON", "error_type": "BAD_JSON"}
            else:
                result = await run_tool(fn_name, args)

            tool_results.append({"tool": fn_name, "args": args, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })


async def _run_stream(client, history, thinking=True):
    """Stream reasoning, answers and tool results while preserving the full wire history."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT + context_prompt()}] + [
        dict(message) for message in history if message.get("role") != "system"
    ]
    tool_count = 0
    for round_index in range(8):
        yield {"type": "round_start", "round": round_index + 1}
        message = None
        async for event in stream_chat(client, messages, thinking=thinking):
            if event["type"] == "message":
                message = event["message"]
            else:
                yield event
        if message is None:
            raise RuntimeError("模型响应不完整，请重试。")
        messages.append(message)
        if not message.get("tool_calls"):
            yield {"type": "done", "history": messages[1:]}
            return
        for call in message["tool_calls"]:
            tool_count += 1
            if tool_count > 24:
                raise RuntimeError("本次工具调用次数已达上限，请缩小查询范围。")
            name = call["function"]["name"]
            yield {"type": "tool_start", "id": call["id"], "tool": name}
            try:
                args = json.loads(call["function"]["arguments"])
                if not isinstance(args, dict):
                    raise ValueError("工具参数必须是对象")
            except (ValueError, TypeError):
                args = {}
                result = {"ok": False, "error": "模型返回的工具参数不合法",
                          "error_type": "BAD_JSON"}
            else:
                result = await run_tool(name, args)
            yield {"type": "tool_result", "id": call["id"],
                   "tool": name, "args": args, "result": result}
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result, ensure_ascii=False)})
    raise RuntimeError("本次分析步骤已达上限，请拆分问题后重试。")


async def run_loop(client, messages, map_context=None, report_context=None):
    with bind_context(messages, map_context, report_context):
        return await _run_loop(client, messages)


async def run_stream(client, history, thinking=True, map_context=None, report_context=None):
    with bind_context(history, map_context, report_context):
        async for event in _run_stream(client, history, thinking):
            yield event
