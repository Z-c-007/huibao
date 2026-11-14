"""Verify running read APIs, isolated ASGI case workflow and optional real LLM calls."""
import argparse
import asyncio
import csv
import io
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import app
from app.services import regulatory_cases as cases
from app.services.db import get_db

BASE='http://127.0.0.1:5173'
NAME='通州运河装备厂（演示）'


def persisted():
    with get_db(include_demo=False) as conn:
        return conn.execute('SELECT id,name,water_used,budget,ST_AsText(geom) FROM public.water_users ORDER BY id').fetchall()


async def workflow():
    # Uses the real source DB and real API implementation; all case writes are
    # isolated from the user's actual ledger in a temporary directory.
    with tempfile.TemporaryDirectory() as directory, patch.object(cases,'CASE_DB',Path(directory)/'cases.db'):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            request={'unit_name':NAME,'year':2026,'quarter':3,'owner':'自动验收监管员','due_date':(cases.now().date()+timedelta(days=7)).isoformat(),'note':'自动验收：核实年度指标及月度计量数据'}
            response=await client.post('/api/regulation/cases',json=request);response.raise_for_status()
            item=response.json()['case']
            assert item['snapshot']['execution_rate']==165
            duplicate=await client.post('/api/regulation/cases',json=request)
            assert not duplicate.json()['created'] and duplicate.json()['case']['id']==item['id']
            forbidden=await client.post(f"/api/regulation/cases/{item['id']}/transition",json={'target':'closed','actor':'验收员','note':'直接办结应当被拒绝','version':item['version']})
            assert forbidden.status_code==422
            stale_version=item['version']
            for target in ['checking','rectifying','review','closed']:
                response=await client.post(f"/api/regulation/cases/{item['id']}/transition",json={'target':target,'actor':'验收员','note':'自动验收：记录核查、整改及复核依据','version':item['version']})
                response.raise_for_status();item=response.json()['case']
            stale=await client.post(f"/api/regulation/cases/{item['id']}/transition",json={'target':'checking','actor':'验收员','note':'旧版本写入应当冲突','version':stale_version})
            assert stale.status_code==409
            listing=(await client.get('/api/regulation/cases')).json()['data']
            assert listing[0]['status']=='closed' and len(listing[0]['events'])==5
            print(json.dumps({'isolated_case_workflow':'passed','events':5,'duplicate_prevented':True,'skip_and_stale_rejected':True},ensure_ascii=False))


def ask(client,prompt,context,expected_tool):
    tools,answer,reasoning,history=[],[],[],None
    with client.stream('POST',BASE+'/api/chat/stream',json={'message':prompt,'thinking':True,'map_context':context}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith('data:'):continue
            event=json.loads(line[5:])
            if event['type']=='error':raise RuntimeError(event['message'])
            if event['type']=='tool_result':
                assert event['result'].get('ok'),event['result'];tools.append(event)
            if event['type']=='content_delta':answer.append(event['text'])
            if event['type']=='reasoning_delta':reasoning.append(event['text'])
            if event['type']=='done':history=event['history']
    assert history and tools and answer and reasoning
    result=next(tool['result'] for tool in tools if tool['tool']==expected_tool)
    print(json.dumps({'live_tools':[tool['tool'] for tool in tools],'reasoning_chars':len(''.join(reasoning)),'answer':''.join(answer)},ensure_ascii=False),flush=True)
    return result,tools


def main(llm=False):
    before=persisted()
    with httpx.Client(timeout=120) as client:
        report=client.get(BASE+'/api/regulation/overview').json()
        assert report['summary']['checked_count']==36
        assert report['summary']['over_budget']==9 and report['summary']['forecast_risk']==10 and report['summary']['invalid_data']==4
        assert report['period']['end']=='2026-09-30'
        mapped=client.get(BASE+'/api/map/water-users').json()
        assert mapped['summary']=={key:value for key,value in report['summary'].items()}
        unknown=client.get(BASE+'/api/regulation/overview?year=2025').json()
        assert unknown['summary']['invalid_data']==36 and all(unit['water_used'] is None for unit in unknown['data'])
        future=client.get(BASE+'/api/regulation/overview?quarter=4').json()
        assert future['summary']['invalid_data']==36
        dossier=client.get(BASE+'/api/regulation/unit',params={'unit_name':NAME}).json()
        assert dossier['data']['inspection_required'] and len(dossier['archive']['monthly'])==9
        agriculture=client.get(BASE+'/api/regulation/unit',params={'unit_name':'通州设施农业园（演示）'}).json()
        assert agriculture['data']['execution_rate']==95 and agriculture['data']['regulatory_status']=='normal'
        ring=[[116.6,39.65],[116.9,39.65],[116.9,39.95],[116.6,39.95],[116.6,39.65]]
        area=client.post(BASE+'/api/map/area-analysis',json={'area':{'coordinates':ring},'year':2026,'quarter':3}).json()
        assert area['summary']['checked_count']==9 and area['period']['end']=='2026-09-30'
        print(json.dumps({'live_summary':report['summary'],'wrong_year_and_future_data_pending':True,'seasonal_agriculture_normal_at_95_percent':True,'area_count':9},ensure_ascii=False),flush=True)
        if llm:
            result,tools=ask(client,'请巡查2026年截至第三季度末的全部单位，区分已超年度指标、预计超年度指标、数据待核实，并生成全量巡查简报供下载。简短回答。',{'available':True,'year':2026,'quarter':3},'inspect_water_budget')
            assert result['summary']['forecast_risk']==10 and result['period']['quarter']==3
            exported=next(tool['result'] for tool in tools if tool['tool']=='generate_inspection_report')
            assert len(list(csv.reader(io.StringIO(exported['report']['csv']))))==37
            assert '不是已发生超用' in exported['report']['markdown']
            result,_=ask(client,'核验这个单位的档案、年度指标版本和月度计量，说明风险证据与核查建议，不要做违法认定。简短回答。',{'available':False,'selected_unit':NAME,'year':2026,'quarter':3},'get_unit_dossier')
            assert result['data']['execution_rate']==165 and result['data']['inspection_required']
    asyncio.run(workflow())
    assert before==persisted()
    print('Verified: persistent business rows unchanged; case tests isolated from user ledger.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--llm',action='store_true');main(parser.parse_args().llm)
