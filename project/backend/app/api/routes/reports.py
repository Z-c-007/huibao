from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.report_drafts import get_draft, list_drafts, list_versions
from ...services.report_documents import export_docx, export_pdf

router = APIRouter(prefix='/reports', tags=['reports'])


@router.get('')
def index():
    return {'ok': True, 'data': list_drafts()}


@router.get('/{report_id}')
def detail(report_id: str, version: int | None = Query(default=None, ge=1)):
    try:
        return {'ok': True, 'report': get_draft(report_id, version), 'versions': list_versions(report_id)}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get('/{report_id}/export/{format}')
def export(report_id: str, format: str, version: int = Query(ge=1)):
    if format not in ('docx', 'pdf'):
        raise HTTPException(422, '仅支持docx和pdf')
    try:
        draft = get_draft(report_id, version)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    content = export_docx(draft) if format == 'docx' else export_pdf(draft)
    mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if format == 'docx' else 'application/pdf'
    return Response(content, media_type=mime, headers={'Content-Disposition': "attachment; filename*=UTF-8''" + quote(draft['filename'] + '.' + format), 'Cache-Control': 'no-store'})
