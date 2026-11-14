"""Versioned report drafts. Immutable server evidence is separate from editable prose."""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .inspection_reports import create_report, _amount

REPORT_DB = Path(__file__).resolve().parents[2] / 'data' / 'report_drafts.db'
PLACEHOLDER = re.compile(r'\{\{([a-z_]+)\}\}')
DEFAULT = {
    'title': '用水执行监管汇总报告',
    'overview': '截至{{period_end}}，本次检查{{checked_count}}家单位，已超年度指标{{over_budget}}家，预计超年度指标{{forecast_risk}}家，数据待核实{{invalid_data}}家。建议优先核查已发生超用的重点对象，同时补齐指标和计量资料。',
    'actions': '对已超指标单位核对有效指标版本与期间计量，优先安排符合监督检查建议条件的对象。\n对预计超指标单位核实季节变化、生产安排和后续用水计划。\n对数据待核实单位先补齐指标下达及月报资料，再重新评价执行情况。',
    'include_details': True, 'include_evidence': True,
}


@contextmanager
def database():
    REPORT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(REPORT_DB, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL, created_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS report_versions(report_id TEXT NOT NULL REFERENCES reports(id), version INTEGER NOT NULL,
        parent_version INTEGER, content TEXT NOT NULL, instruction TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(report_id,version));
    ''')
    try:
        yield conn
    finally:
        conn.close()


def facts(snapshot):
    summary, scope = snapshot['summary'], snapshot['scope']
    period = snapshot.get('period') or {}
    reasons = summary.get('data_pending_reasons', {})
    return {'period_start': period.get('start', '未提供'), 'period_end': period.get('end', '当前记录'),
            'period_label': period.get('label', '无周期快照'), 'district': scope['district'], 'industry': scope['industry'],
            **{key: str(summary.get(key, 0)) for key in ('checked_count', 'over_budget', 'forecast_risk', 'normal', 'invalid_data', 'inspection_required')},
            **{key: _amount(summary.get(key)) for key in ('total_water_used', 'total_budget', 'total_over_budget_amount')},
            **{key: str(reasons.get(key, 0)) for key in ('indicator_pending', 'missing_monthly', 'other')},
            'inspection_threshold': '20%', 'annual_threshold': '100%'}


def validate_content(content, snapshot):
    if set(content) != set(DEFAULT):
        raise ValueError('报告编辑字段不完整或包含未知字段')
    for key in ('include_details', 'include_evidence'):
        if type(content[key]) is not bool:
            raise ValueError('清单和证据开关必须为布尔值')
    allowed = facts(snapshot)
    for key in ('title', 'overview', 'actions'):
        text = content[key]
        if not isinstance(text, str) or not text.strip() or len(text) > (100 if key == 'title' else 6000):
            raise ValueError('标题或正文为空或超过长度限制')
        if any(name not in allowed for name in PLACEHOLDER.findall(text)):
            raise ValueError('请仅引用 get_report_draft 返回的事实占位符')
        stripped = PLACEHOLDER.sub('', text)
        if '{{' in stripped or '}}' in stripped or re.search(r'[0-9０-９]', stripped):
            raise ValueError('统计数字和日期必须使用事实占位符，不能手写或改动数字')
        if re.search(r'[<>\x00-\x08\x0b\x0c\x0e-\x1f]', text):
            raise ValueError('报告正文不支持HTML或控制字符')
    if re.search(r'[^\w\s\u4e00-\u9fff{}]', content['title']):
        raise ValueError('标题请使用文字、数字占位符和空格')


def expand(text, snapshot):
    values = facts(snapshot)
    return PLACEHOLDER.sub(lambda match: values[match[1]], text)


def attachment(row, version, latest):
    snapshot, content = json.loads(row['snapshot']), json.loads(version['content'])
    base = create_report(snapshot)
    markdown = base['markdown']
    if not content['include_details']:
        markdown = re.sub(r'## 受检单位清单.*?(?=数据待核实主要原因|## 风险证据与预测|## 核查建议)', '', markdown, flags=re.S)
    if not content['include_evidence']:
        markdown = re.sub(r'## 风险证据与预测.*?(?=## 核查建议)', '', markdown, flags=re.S)
        markdown = markdown.replace('完整问题见单位证据', '完整问题见CSV单位清单')
    if not content['include_details']:
        markdown = markdown.replace('清单包含全部受检单位，不受地图显示筛选影响；数值单位沿用原始入库口径。', '完整单位清单另附CSV，不受地图显示筛选影响；数值单位沿用原始入库口径。')
    markdown = re.sub(r'## 核查建议.*?(?=## 数据口径)', lambda _: '## 核查建议\n\n' + expand(content['actions'], snapshot) + '\n\n', markdown, flags=re.S)
    title = expand(content['title'], snapshot)
    markdown = markdown.replace('# 用水执行监管巡查简报', '# ' + title, 1)
    markdown = re.sub(r'生成时间：[^\n]+', '生成时间：' + version['created_at'], markdown, count=1)
    markdown = markdown.replace('## 巡查概览', '## 汇总结论\n\n' + expand(content['overview'], snapshot) + '\n\n## 巡查概览', 1)
    # Mandatory evidence boundary survives every edit, including a short report.
    markdown += '\n报告版本：V' + str(version['version']) + '。本稿引用同一巡查数据快照，改稿不会更新原始统计。\n'
    markdown += '监管判断须经业务核实。预测不代表已发生超用，本报告不作违法或处罚认定。\n'
    if snapshot.get('period'):
        markdown += '北京案例依据：《北京市非居民用水单位用水预算管理办法》监督检查条款。\nhttps://www.beijing.gov.cn/zhengce/zhengcefagui/202310/t20231030_3290091.html\n'
    return {**base, 'filename': title + '_V' + str(version['version']), 'generated_at': version['created_at'],
            'title': title, 'markdown': markdown, 'report_id': row['id'], 'version': version['version'],
            'latest_version': latest, 'parent_version': version['parent_version'], 'instruction': version['instruction'],
            'snapshot_hash': row['snapshot_hash'], 'editable': content, 'facts': facts(snapshot)}


def get_draft(report_id, version=None):
    with database() as conn:
        row = conn.execute('SELECT * FROM reports WHERE id=?', (report_id,)).fetchone()
        if row is None:
            raise LookupError('报告不存在，请重新生成或从已保存报告中选择')
        latest = conn.execute('SELECT MAX(version) FROM report_versions WHERE report_id=?', (report_id,)).fetchone()[0]
        selected = conn.execute('SELECT * FROM report_versions WHERE report_id=? AND version=?', (report_id, version or latest)).fetchone()
        if selected is None:
            raise LookupError('报告版本不存在')
        return attachment(row, selected, latest)


def create_draft(snapshot):
    snapshot = deepcopy(snapshot)
    snapshot.pop('report', None)
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    report_id, timestamp = uuid4().hex, datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    with database() as conn:
        conn.execute('INSERT INTO reports VALUES(?,?,?,?)', (report_id, encoded, hashlib.sha256(encoded.encode()).hexdigest(), timestamp))
        conn.execute('INSERT INTO report_versions VALUES(?,?,?,?,?,?)', (report_id, 1, None, json.dumps(DEFAULT, ensure_ascii=False), '首次生成', timestamp))
        conn.commit()
    return get_draft(report_id)


def revise_draft(report_id, parent_version, expected_latest, changes, instruction):
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM reports WHERE id=?', (report_id,)).fetchone()
        previous = conn.execute('SELECT * FROM report_versions WHERE report_id=? AND version=?', (report_id, parent_version)).fetchone()
        if row is None or previous is None:
            raise LookupError('报告或版本不存在')
        latest = conn.execute('SELECT MAX(version) FROM report_versions WHERE report_id=?', (report_id,)).fetchone()[0]
        if latest != expected_latest:
            raise ValueError('报告已在另一轮更新，请重新选择最新版本后修改')
        content = {**json.loads(previous['content']), **changes}
        validate_content(content, json.loads(row['snapshot']))
        timestamp = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
        conn.execute('INSERT INTO report_versions VALUES(?,?,?,?,?,?)', (report_id, latest + 1, parent_version, json.dumps(content, ensure_ascii=False), instruction[:2000], timestamp))
        conn.commit()
    return get_draft(report_id, latest + 1)


def list_drafts():
    with database() as conn:
        rows = conn.execute('SELECT r.*, MAX(v.version) AS latest FROM reports r JOIN report_versions v ON r.id=v.report_id GROUP BY r.id ORDER BY r.created_at DESC LIMIT 50').fetchall()
        return [{'report_id': row['id'], 'created_at': row['created_at'], 'latest_version': row['latest'],
                 'scope': json.loads(row['snapshot'])['scope']} for row in rows]


def list_versions(report_id):
    with database() as conn:
        return [dict(row) for row in conn.execute('SELECT version,parent_version,instruction,created_at FROM report_versions WHERE report_id=? ORDER BY version DESC', (report_id,))]
