"""Source-backed Markdown and CSV exports. No generated statistics or file writes."""
import csv
import io
import re
from datetime import datetime, timedelta, timezone


def _text(value):
    return re.sub(r"([\\`*_{}\[\]()#+.!|<>])", r"\\\1", str(value)).replace("\r", " ").replace("\n", " ")


def _amount(value):
    return "—" if value is None else format(value, ",.4f").rstrip("0").rstrip(".")


def _rate(unit):
    value = unit["execution_rate"]
    if value is None:
        return "—"
    if unit["budget_status"] == "over_budget" and value <= 100:
        return ">100%"
    return _amount(value) + "%"


def _csv_cell(value):
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))):
        return "'" + value
    return "" if value is None else value


def create_report(report):
    units = report.get("all_units", report["data"])
    summary = report["summary"]
    timestamp = datetime.now(timezone(timedelta(hours=8)))
    scope = report["scope"]
    title = "地图圈选区域" if report.get("area") else scope["district"]
    selected = report.get('period')
    lines = ["# 用水执行监管巡查简报", "", f"生成时间：{timestamp.isoformat(timespec='seconds')}",
             f"检查范围：{_text(title)} · {_text(scope['industry'])}",
             f"数据快照：{report.get('generated_at', '当前查询')}", "", "## 巡查概览", "",
             f"- 受检单位：{summary['checked_count']} 家；已超指标 {summary['over_budget']} 家；预计超指标 {summary.get('forecast_risk', summary['near_limit'])} 家；正常 {summary['normal']} 家；数据待核实 {summary['invalid_data']} 家。",
             f"- {'核验通过单位' if selected else '已记录'}实际用水合计：{_amount(summary.get('total_water_used'))}；对应指标合计：{_amount(summary.get('total_budget'))}。",
             f"- 超额用水合计：{_amount(summary['total_over_budget_amount'])}。",
             (f"- 统计期间：{selected['start']}至{selected['end']}；比较口径：累计用水/同年度有效指标；水量单位：立方米。\n- 已发生年度超指标严格超过20%的监督检查建议对象：{summary.get('inspection_required', 0)} 家（北京案例，不是违法认定）。" if selected else f"- 无周期原始记录快照；{report['thresholds']['near_limit_percent']}%仅为展示阈值，不能作为年度监管依据。"), "",
             "## 受检单位清单", "", "| 单位 | 行业 | 区县 | 状态 | 累计用水 | 年度指标 | 执行比例 | 已发生超用 |",
             "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |"]
    for unit in units:
        cells = [unit["name"], unit["industry"], unit["district"], unit["status_label"],
                 _amount(unit["water_used"]), _amount(unit["budget"]), _rate(unit), _amount(unit["over_budget_amount"])]
        lines.append("| " + " | ".join(_text(cell) for cell in cells) + " |")
    if selected:
        reasons = summary.get('data_pending_reasons', {})
        lines.extend(['', f"数据待核实主要原因：指标待下达 {reasons.get('indicator_pending', 0)} 家；月报缺失或未核实 {reasons.get('missing_monthly', 0)} 家；其他口径问题 {reasons.get('other', 0)} 家。分类先列指标下达问题，完整问题见单位证据。", '', '## 风险证据与预测', '', report.get('forecast_method') or '未提供可用预测方法。'])
        for unit in units:
            if unit.get('regulatory_status') == 'normal':
                continue
            lines.extend(['', f"### {_text(unit['name'])} · {_text(unit['status_label'])}"])
            if unit.get('forecast_annual') is not None:
                lines.append(f"- 预计全年：{_amount(unit['forecast_annual'])} 立方米；这是情景外推，不是已发生超用。")
            lines.extend('- ' + _text(line) for line in unit.get('evidence', []))
    if not units:
        lines.extend(["", "该范围内没有已入库单位，本次没有生成异常对象。"])
    lines.extend(["", "## 核查建议", "",
                  "- 对已发生超指标单位核对有效指标版本、期间计量和管理范围；超用超过20%的按北京案例优先监督检查。",
                  "- 对预计超指标单位核实生产与季节变化、后续用水安排；预测本身不是违法证据。",
                  "- 对数据待核实单位先核验缺报、指标下达、周期和水源用途，不能把缺报补零或认定正常。",
                  "- 分析基于当前记录；异常原因需要进一步业务核实。", "", "## 数据口径", "",
                  report.get("note", "按当前入库记录检查。"),
                  "清单包含全部受检单位，不受地图显示筛选影响；数值单位沿用原始入库口径。"])
    if not summary.get("totals_complete", True):
        lines.append("部分记录无有效预算或用水量；周期监管合计仅纳入核验通过单位，不提供完整总体执行比例。")
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["单位名称", "行业", "区县", "街道", "累计用水", "年度指标", "执行比例(%)", "监管状态", "已发生超用", "超额比例(%)", "经度", "纬度"] + (["统计起始", "统计截至", "水源", "用途", "指标版本", "预计全年", "预计超用", "监督检查建议", "证据及数据问题"] if selected else []))
    for unit in units:
        values = [unit.get(key) for key in ("name", "industry", "district", "street", "water_used", "budget", "execution_rate", "status_label", "over_budget_amount", "over_budget_percent", "lon", "lat")]
        if selected:
            values += [selected['start'], selected['end'], unit.get('water_source'), unit.get('purpose'), unit.get('indicator_version'), unit.get('forecast_annual'), unit.get('forecast_over_amount'), '建议检查' if unit.get('inspection_required') else '', '；'.join(unit.get('evidence', []))]
        writer.writerow([_csv_cell(value) for value in values])
    return {"filename": "用水预算巡查_" + timestamp.strftime("%Y%m%d_%H%M%S"),
            "generated_at": timestamp.isoformat(timespec="seconds"), "markdown": "\n".join(lines) + "\n", "csv": output.getvalue()}
