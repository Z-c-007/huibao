"""Domain and API regression checks using isolated case storage and synthetic records."""
import copy
import csv
import io
import json
from collections import Counter
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx

from app.services.regulatory import evaluate_profile, period, PROFILE_FILE
from app.services.budget_data import build_inspection
from app.services.inspection_reports import create_report
from app.services import regulatory_cases as cases
from app.services.validator import validate_args
from app.schemas.regulatory import CaseCreate, CaseTransition
from pydantic import ValidationError

UNIT = dict(name='测试单位', industry='制造业', lon=116.72, lat=39.8, district='通州区', street='新华街道', id=1)


def profile(used=60, annual=100, agriculture=False, months=9):
    shares = [2,2,4,10,15,18,18,17,10,2,1,1] if agriculture else [8,6,8,8,8,8,8,8,8,10,10,10]
    return dict(demo=True, water_source='公共供水', purpose='生产', management_type='计划用水管理', meters=[{'id': 'M1'}],
                indicator=dict(year=2026, annual_volume=annual, state='issued', version='V1', source='公共供水', purpose='生产',
                               effective_from='2026-01-01', effective_to='2026-12-31', monthly_shares=[value/100 for value in shares]),
                monthly=[dict(month=i, volume=used if i==1 else 0, source='公共供水', meter_id='M1', quality='verified') for i in range(1, months+1)])


class DomainTests(unittest.TestCase):
    def test_demo_covers_pending_indicators_and_missing_meter_data_separately(self):
        catalog=json.loads(PROFILE_FILE.read_text(encoding='utf-8'))
        units=[evaluate_profile({**UNIT,'name':item['name']},item) for item in catalog]
        report=build_inspection(units,year=2026,quarter=3)
        self.assertEqual(Counter(unit['regulatory_status'] for unit in units), {'over_limit':9,'forecast_risk':10,'data_pending':4,'normal':13})
        self.assertEqual(report['summary']['data_pending_reasons'], {'indicator_pending':2,'missing_monthly':2,'other':0})
    def test_seasonality_changes_forecast_without_changing_actual_ratio(self):
        normal = evaluate_profile(UNIT, profile(95, agriculture=True))
        risk = evaluate_profile(UNIT, profile(95))
        self.assertEqual(normal['regulatory_status'], 'normal')
        self.assertEqual(risk['regulatory_status'], 'forecast_risk')
        self.assertEqual(normal['execution_rate'], risk['execution_rate'])
        self.assertEqual(risk['forecast_annual'], 135.71)

    def test_inspection_trigger_uses_strict_unrounded_twenty_percent(self):
        exact = evaluate_profile(UNIT, profile(120))
        tiny = evaluate_profile(UNIT, profile('120.00004'))
        self.assertFalse(exact['inspection_required'])
        self.assertTrue(tiny['inspection_required'])
        self.assertEqual(tiny['execution_rate'], 120)

    def test_exact_annual_limit_is_not_occurred_overrun(self):
        result = evaluate_profile(UNIT, profile(100, months=12), quarter=4)
        self.assertEqual(result['regulatory_status'], 'normal')
        self.assertEqual(result['over_budget_amount'], 0)

    def test_pending_indicator_is_not_zero_or_normal(self):
        data = profile(); data['indicator']['state'] = 'pending'
        result = evaluate_profile(UNIT, data)
        self.assertEqual(result['regulatory_status'], 'data_pending')
        self.assertIsNone(result['budget'])
        self.assertIsNone(result['execution_rate'])
        self.assertIsNone(result['forecast_annual'])

    def test_missing_duplicate_bad_meter_and_different_source_reject_comparison(self):
        for mutate in [lambda data: data['monthly'].pop(),
                       lambda data: data['monthly'].append(copy.deepcopy(data['monthly'][0])),
                       lambda data: data['monthly'][0].update(volume=None),
                       lambda data: data['monthly'][0].update(meter_id='FOREIGN'),
                       lambda data: data['monthly'][0].update(source='地下水')]:
            data = profile(); mutate(data)
            result = evaluate_profile(UNIT, data)
            self.assertEqual(result['regulatory_status'], 'data_pending')
            self.assertIsNone(result['execution_rate'])
            self.assertIsNone(result['over_budget_amount'])

    def test_wrong_year_future_quarter_and_expired_version_not_silently_reused(self):
        for year, quarter, change in [(2025,3,False),(2026,4,False),(2026,3,True)]:
            data = profile()
            if change: data['indicator']['effective_to']='2026-06-30'
            result = evaluate_profile(UNIT, data, year, quarter)
            self.assertEqual(result['regulatory_status'], 'data_pending')
            self.assertIsNone(result['execution_rate'])
            if year != 2026:self.assertIsNone(result['water_used'])

    def test_missing_season_plan_does_not_imply_full_year_normal(self):
        data=profile(60);data['indicator']['monthly_shares']=[]
        result=evaluate_profile(UNIT,data)
        self.assertEqual(result['regulatory_status'],'data_pending')
        self.assertEqual(result['execution_rate'],60)
        self.assertIsNone(result['forecast_annual'])

    def test_missing_archive_is_pending_not_annual_snapshot(self):
        result = evaluate_profile(UNIT, None)
        self.assertEqual(result['regulatory_status'], 'data_pending')
        self.assertIsNone(result['water_used'])

    def test_permit_cap_is_checked(self):
        data = profile(); data.update(management_type='取水许可管理', permit_id='P1', permit_volume=80)
        self.assertEqual(evaluate_profile(UNIT,data)['regulatory_status'], 'data_pending')

    def test_report_distinguishes_occurrence_forecast_and_invalid_data(self):
        units = [evaluate_profile(UNIT,profile(140)), evaluate_profile({**UNIT,'name':'预测单位'},profile(80)), evaluate_profile({**UNIT,'name':'缺报单位'},None)]
        report = build_inspection(units, status_filter='over_budget',year=2026,quarter=3)
        self.assertEqual(report['summary']['checked_count'],3)
        self.assertEqual(report['summary']['forecast_risk'],1)
        self.assertEqual(report['summary']['inspection_required'],1)
        self.assertEqual(report['summary']['data_pending_reasons']['missing_monthly'],1)
        artifact = create_report(report)
        rows=list(csv.reader(io.StringIO(artifact['csv'])))
        self.assertEqual(len(rows),4)
        self.assertIn('统计截至',rows[0])
        self.assertIn('2026-09-30', artifact['markdown'])
        self.assertIn('不是已发生超用', artifact['markdown'])

    def test_invalid_period_is_rejected_in_api_tool_and_schema(self):
        with self.assertRaises(ValueError): period(2026,0)
        with self.assertRaises(ValueError): period(True,3)
        self.assertIsNotNone(validate_args('inspect_water_budget', {'quarter': True}))
        self.assertIsNotNone(validate_args('get_unit_dossier', {'year': 2019}))
        with self.assertRaises(ValidationError): CaseTransition(target='closed',note='已核实完成',actor='监管员',version=True)


class CaseTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.storage=patch.object(cases,'CASE_DB',Path(self.directory.name)/'cases.db');self.storage.start()
        self.clock=patch.object(cases,'now',return_value=datetime(2026,10,14,tzinfo=timezone(timedelta(hours=8))));self.clock.start()
        self.source={'ok':True,'data':evaluate_profile(UNIT,profile(140))}
        self.query=patch('app.services.regulatory.unit_dossier',return_value=self.source);self.query.start()
    def tearDown(self):
        self.query.stop();self.clock.stop();self.storage.stop();self.directory.cleanup()
    def create(self):
        return cases.create_case('测试单位',2026,3,'监管员','2026-10-21','核实计量和年度指标版本')['case']
    def move(self,case,target,note='已核实资料并记录办理依据'):
        return cases.transition_case(case['id'],target,note,'监管员',case['version'])['case']

    def test_complete_workflow_is_persistent_with_immutable_evidence(self):
        item=self.create()
        self.source['data']['evidence'].append('后来变化')
        self.assertNotIn('后来变化',cases.list_cases()[0]['snapshot']['evidence'])
        for next_state in ['checking','rectifying','review','closed']:
            item=self.move(item,next_state)
        saved=cases.list_cases()[0]
        self.assertEqual(saved['status'],'closed')
        self.assertEqual(len(saved['events']),5)
        self.assertEqual(saved['version'],5)
        self.assertEqual(self.move(saved,'checking')['status'],'checking')

    def test_duplicate_create_returns_existing_case(self):
        first=self.create(); second=self.create()
        self.assertEqual(first['id'],second['id'])
        self.assertEqual(len(cases.list_cases()),1)

    def test_cannot_skip_review_or_update_with_stale_version(self):
        item=self.create()
        with self.assertRaises(ValueError):self.move(item,'closed')
        current=self.move(item,'checking')
        with self.assertRaises(RuntimeError):self.move(item,'rectifying')
        self.assertEqual(cases.list_cases()[0]['status'],current['status'])

    def test_missing_notes_past_deadlines_and_normal_units_are_rejected(self):
        item=self.create()
        with self.assertRaises(ValueError):self.move(item,'checking','')
        with self.assertRaises(ValueError):cases.create_case('测试单位',2026,3,'监管员','2026-10-13','核验历史用水记录')
        self.source['data']['regulatory_status']='normal'
        with self.assertRaises(ValueError):self.create()

    def test_overdue_is_shanghai_date_and_closed_cases_excluded(self):
        item=self.create()
        with patch.object(cases,'now',return_value=datetime(2026,10,22,tzinfo=timezone(timedelta(hours=8)))):
            self.assertTrue(cases.list_cases()[0]['overdue'])
            for next_state in ['checking','review','closed']:item=self.move(item,next_state)
            self.assertFalse(cases.list_cases()[0]['overdue'])


class APITests(unittest.IsolatedAsyncioTestCase):
    async def test_mutation_validation_and_conflict_status(self):
        from app.main import app
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            bad=await client.post('/api/regulation/cases',json={'unit_name':'测试单位','owner':'','note':'x','due_date':'invalid','snapshot':{'forged':True}})
            self.assertEqual(bad.status_code,422)
            with patch('app.api.routes.regulatory.transition_case',side_effect=RuntimeError('记录已更新')):
                conflict=await client.post('/api/regulation/cases/id/transition',json={'target':'checking','note':'核实数据并记录','actor':'监管员','version':1})
                self.assertEqual(conflict.status_code,409)
            bad_period=await client.get('/api/regulation/overview?quarter=0')
            self.assertEqual(bad_period.status_code,422)


if __name__=='__main__':unittest.main()
