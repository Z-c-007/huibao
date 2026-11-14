"""Real streaming model -> saved report -> two dialogue revisions -> exact-version exports."""
import io
import json
import sys
from zipfile import ZipFile

import httpx

BASE = 'http://127.0.0.1:5173'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def ask(client, text, history, report=None):
    payload = {'message': text, 'history': history, 'thinking': True}
    if report:
        payload['report_context'] = {'report_id': report['report_id'], 'version': report['version']}
    answer, calls, next_history = [], [], None
    with client.stream('POST', BASE + '/api/chat/stream', json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith('data:'): continue
            event = json.loads(line[5:])
            if event['type'] == 'error': raise RuntimeError(event['message'])
            if event['type'] == 'tool_result': calls.append(event)
            if event['type'] == 'content_delta': answer.append(event['text'])
            if event['type'] == 'done': next_history = event['history']
    successful = [call for call in calls if call['result'].get('ok') and 'report' in call['result']]
    if not successful:
        raise RuntimeError(json.dumps({'calls': calls, 'answer': ''.join(answer)}, ensure_ascii=False))
    saved = successful[-1]['result']['report']
    print(json.dumps({'version': saved['version'], 'tools': [call['tool'] for call in calls], 'snapshot_hash': saved['snapshot_hash'], 'answer': ''.join(answer)[:350]}, ensure_ascii=False), flush=True)
    assert next_history
    return saved, next_history


def main():
    with httpx.Client(timeout=300, trust_env=False) as client:
        first, history = ask(client, '生成2026年截至第三季度末全库用水执行监管汇总报告，需要完整单位清单和风险证据，供Word和PDF下载。简短回答。', [])
        second, history = ask(client, '这份报告太长了，改成给领导看的精简汇总，突出建议监督检查的对象数量，关闭完整单位清单和逐项证据，保留统计和口径，保存新版。', history, first)
        assert second['version'] == 2 and '## 受检单位清单' not in second['markdown']
        third, history = ask(client, '继续调整这份报告，标题改为用水执行监管重点汇总，核查建议分别说明已超指标、预测风险、指标未下达与月报缺失的跟进动作，仍保留精简形式，保存新版。', history, second)
        assert third['version'] == 3 and third['title'] == '用水执行监管重点汇总'
        assert first['snapshot_hash'] == second['snapshot_hash'] == third['snapshot_hash']
        assert first['csv'] == second['csv'] == third['csv']
        saved_id = first['report_id']
        assert client.get(BASE + f'/api/reports/{saved_id}?version=1').json()['report']['markdown'] == first['markdown']
        for version in (1, 3):
            pdf = client.get(BASE + f'/api/reports/{saved_id}/export/pdf?version={version}')
            pdf.raise_for_status(); assert pdf.content.startswith(b'%PDF-')
            word = client.get(BASE + f'/api/reports/{saved_id}/export/docx?version={version}')
            word.raise_for_status()
            with ZipFile(io.BytesIO(word.content)) as archive:
                assert f'V{version}' in archive.read('word/document.xml').decode()
        print('Verified: real multi-turn revisions V1/V2/V3; immutable evidence; old version retained; Word/PDF export through frontend proxy.', flush=True)


if __name__ == '__main__': main()
