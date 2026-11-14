import asyncio
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import httpx
from app.main import app
from app.schemas.chat import ReportContext
from app.services import report_drafts as drafts
from app.services.agent_context import bind_context
from app.services.budget_data import build_inspection, classify_unit
from app.services.report_documents import export_docx, export_pdf
from app.services.tools import get_report_draft, revise_inspection_report
from app.services.validator import validate_args


class ReportDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(drafts, 'REPORT_DB', Path(self.temp.name) / 'reports.db')
        self.patch.start()
        self.snapshot = build_inspection([classify_unit((1, '测试单位', '制造业', 120, 100, 116.7, 39.8, '通州区', '测试街道'))], year=2026, quarter=3)
        self.first = drafts.create_draft(self.snapshot)

    def tearDown(self):
        self.patch.stop(); self.temp.cleanup()

    def test_saved_versions_snapshot_and_branch(self):
        second = drafts.revise_draft(self.first['report_id'], 1, 1, {'overview': '重点核查{{over_budget}}家已超指标单位。', 'include_details': False}, '精简')
        self.snapshot['summary']['over_budget'] = 999
        self.assertIn('重点核查1家', second['markdown'])
        self.assertNotIn('## 受检单位清单', second['markdown'])
        self.assertEqual(second['snapshot_hash'], self.first['snapshot_hash'])
        self.assertEqual(second['csv'], self.first['csv'])
        self.assertEqual(drafts.get_draft(self.first['report_id'], 1)['markdown'], self.first['markdown'])
        third = drafts.revise_draft(self.first['report_id'], 1, 2, {'title': '恢复完整巡查报告'}, '基于旧稿恢复')
        self.assertEqual(third['parent_version'], 1)
        self.assertIn('## 受检单位清单', third['markdown'])
        self.assertEqual(len(drafts.list_versions(self.first['report_id'])), 3)
        self.assertEqual(drafts.list_drafts()[0]['latest_version'], 3)

    def test_stale_revision_rejected_without_extra_version(self):
        drafts.revise_draft(self.first['report_id'], 1, 1, {'title': '重点报告'}, '改标题')
        with self.assertRaisesRegex(ValueError, '另一轮'):
            drafts.revise_draft(self.first['report_id'], 1, 1, {'title': '过期稿'}, '冲突')
        self.assertEqual(len(drafts.list_versions(self.first['report_id'])), 2)

    def test_numerical_and_unknown_edits_rejected(self):
        for changes in ({'overview': '已超指标999家'}, {'overview': '共{{invented}}家'}, {'summary': {}}, {'include_details': 1}, {'title': '<script>'}):
            with self.assertRaises(ValueError):
                drafts.revise_draft(self.first['report_id'], 1, 1, changes, '非法修改')
        self.assertEqual(len(drafts.list_versions(self.first['report_id'])), 1)

    def test_context_uses_saved_evidence_not_client_history(self):
        context = ReportContext(report_id=self.first['report_id'], version=1)
        with bind_context([{'role': 'user', 'content': '突出重点'}], report_context=context):
            self.assertEqual(get_report_draft()['report']['facts']['checked_count'], '1')
            changed = revise_inspection_report(overview='核查{{over_budget}}家已超指标单位。', include_evidence=False)
            self.assertTrue(changed['ok']); self.assertEqual(changed['report']['version'], 2)
            self.assertEqual(changed['report']['instruction'], '突出重点')
        self.assertFalse(get_report_draft()['ok'])

    def test_export_structure_and_api_exact_version(self):
        # Service export integration. Author/render QA uses the bundled runtime separately.
        with ZipFile(io.BytesIO(export_docx(self.first))) as archive:
            xml = archive.read('word/document.xml').decode()
            self.assertIn('测试单位', xml); self.assertIn('tblHeader', xml)
            self.assertIn('用水执行监管汇总报告', xml)
        self.assertTrue(export_pdf(self.first).startswith(b'%PDF-'))
        async def requests():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                draft_id = self.first['report_id']
                for format, signature in [('pdf', b'%PDF-'), ('docx', b'PK')]:
                    response = await client.get(f'/api/reports/{draft_id}/export/{format}?version=1')
                    self.assertEqual(response.status_code, 200); self.assertTrue(response.content.startswith(signature))
                    self.assertIn('filename*=UTF-8', response.headers['content-disposition'])
                self.assertEqual((await client.get(f'/api/reports/{draft_id}?version=99')).status_code, 404)
                self.assertEqual((await client.get(f'/api/reports/{draft_id}/export/pdf?version=99')).status_code, 404)
                self.assertEqual((await client.get(f'/api/reports/{draft_id}/export/exe?version=1')).status_code, 422)
                self.assertEqual((await client.get(f'/api/reports/{draft_id}/export/pdf')).status_code, 422)
                invalid = await client.post('/api/chat/stream', json={'message': '改稿', 'report_context': {'report_id': '0' * 32, 'version': 1}})
                self.assertEqual(invalid.status_code, 404)
        asyncio.run(requests())

    def test_prose_and_switch_validation(self):
        self.assertIsNone(validate_args('revise_inspection_report', {'overview': '建议核验“有效指标”；不能推断原因。', 'include_details': False}))
        self.assertIsNotNone(validate_args('revise_inspection_report', {'include_details': 1}))


if __name__ == '__main__':
    unittest.main()
