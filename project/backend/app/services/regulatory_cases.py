"""Local supervision work records with evidence snapshots and checked transitions."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

CASE_DB = Path(__file__).resolve().parents[2] / 'data' / 'regulatory_cases.db'
TZ = timezone(timedelta(hours=8))
STATUS_NAMES = {'pending': '待核查', 'checking': '核查中', 'rectifying': '整改中', 'review': '待复核', 'closed': '已办结'}
TRANSITIONS = {'pending': ['checking'], 'checking': ['rectifying', 'review'],
               'rectifying': ['review'], 'review': ['rectifying', 'closed'], 'closed': ['checking']}


def now():
    return datetime.now(TZ)


@contextmanager
def database():
    CASE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CASE_DB, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY, unit_name TEXT NOT NULL, year INTEGER NOT NULL, quarter INTEGER NOT NULL,
        risk_type TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, due_date TEXT NOT NULL,
        snapshot TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, version INTEGER NOT NULL,
        UNIQUE(unit_name, year, quarter, risk_type));
      CREATE TABLE IF NOT EXISTS case_events (
        id INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), from_status TEXT,
        to_status TEXT NOT NULL, note TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL);
    ''')
    try:
        yield conn
    finally:
        conn.close()


def as_case(conn, row):
    case = dict(row)
    case['snapshot'] = json.loads(case['snapshot'])
    case['status_label'] = STATUS_NAMES[case['status']]
    case['overdue'] = case['status'] != 'closed' and case['due_date'] < now().date().isoformat()
    case['allowed_next'] = TRANSITIONS[case['status']]
    case['events'] = [dict(event) for event in conn.execute('SELECT * FROM case_events WHERE case_id=? ORDER BY id', (case['id'],))]
    return case


def list_cases(unit_name=None):
    with database() as conn:
        sql, args = 'SELECT * FROM cases', []
        if unit_name is not None:
            sql += ' WHERE unit_name=?'
            args.append(unit_name)
        rows = conn.execute(sql + ' ORDER BY updated_at DESC, id', args).fetchall()
        return [as_case(conn, row) for row in rows]


def create_case(unit_name, year, quarter, owner, due_date, note):
    from .regulatory import unit_dossier
    # The client cannot send amounts, policy conclusions or a forged snapshot.
    dossier = unit_dossier(unit_name, year, quarter)
    if not dossier['ok']:
        raise LookupError('单位不存在')
    unit = dossier['data']
    if unit['regulatory_status'] == 'normal':
        raise ValueError('当前单位没有预警，请先明确核查依据')
    if due_date < now().date().isoformat():
        raise ValueError('办理期限不能早于今天')
    timestamp, case_id = now().isoformat(timespec='seconds'), uuid4().hex
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute('SELECT * FROM cases WHERE unit_name=? AND year=? AND quarter=? AND risk_type=?',
                                (unit_name, year, quarter, unit['regulatory_status'])).fetchone()
        if existing:
            return {'ok': True, 'created': False, 'case': as_case(conn, existing), 'message': '该期间同类预警已建立核查记录'}
        conn.execute('INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     (case_id, unit_name, year, quarter, unit['regulatory_status'], 'pending', owner,
                      due_date, json.dumps(unit, ensure_ascii=False), timestamp, timestamp, 1))
        conn.execute('INSERT INTO case_events(case_id, from_status, to_status, note, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                     (case_id, None, 'pending', note, owner, timestamp))
        conn.commit()
        return {'ok': True, 'created': True, 'case': as_case(conn, conn.execute('SELECT * FROM cases WHERE id=?', (case_id,)).fetchone())}


def transition_case(case_id, target, note, actor, version):
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM cases WHERE id=?', (case_id,)).fetchone()
        if row is None:
            raise LookupError('核查记录不存在')
        if row['version'] != version:
            raise RuntimeError('记录已被更新，请刷新后再操作')
        if target not in TRANSITIONS[row['status']]:
            raise ValueError('不允许跳过核查或复核环节')
        if not note.strip() or not actor.strip():
            raise ValueError('必须填写办理说明和记录人')
        timestamp = now().isoformat(timespec='seconds')
        conn.execute('UPDATE cases SET status=?, updated_at=?, version=version+1 WHERE id=? AND version=?', (target, timestamp, case_id, version))
        conn.execute('INSERT INTO case_events(case_id, from_status, to_status, note, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                     (case_id, row['status'], target, note, actor, timestamp))
        conn.commit()
        return {'ok': True, 'case': as_case(conn, conn.execute('SELECT * FROM cases WHERE id=?', (case_id,)).fetchone())}
