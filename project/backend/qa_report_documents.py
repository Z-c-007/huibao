"""Author samples with the Codex bundled Python; all report writes are isolated."""
import json
import urllib.request
from pathlib import Path
from unittest.mock import patch

from app.services import report_drafts as drafts
from app.services.report_documents import export_docx, export_pdf

output = Path(__file__).resolve().parents[1] / 'tmp' / 'report-qa'
output.mkdir(parents=True, exist_ok=True)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
snapshot = json.loads(opener.open('http://127.0.0.1:8000/api/regulation/overview', timeout=30).read())
with patch.object(drafts, 'REPORT_DB', output / 'qa.db'):
    full = drafts.create_draft(snapshot)
    brief = drafts.revise_draft(full['report_id'], 1, 1, {
        'title': '用水执行监管重点汇总',
        'overview': '本次检查{{checked_count}}家单位。建议优先核查符合监督检查建议条件的{{inspection_required}}家对象，并分别跟进预测风险及数据待核实事项。',
        'include_details': False, 'include_evidence': False,
    }, '精简汇总并突出监督检查对象')
    for name, report in [('full', full), ('brief', brief)]:
        (output / (name + '.docx')).write_bytes(export_docx(report))
        (output / (name + '.pdf')).write_bytes(export_pdf(report))
        (output / (name + '.md')).write_text(report['markdown'], encoding='utf-8')
    print(json.dumps({'units': snapshot['summary']['checked_count'], 'samples': ['full', 'brief'], 'output': str(output)}, ensure_ascii=False))
