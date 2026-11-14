from fastapi import APIRouter, HTTPException, Query

from ...schemas.regulatory import CaseCreate, CaseTransition
from ...services.regulatory import regulatory_inventory, unit_dossier
from ...services.regulatory_cases import list_cases, create_case, transition_case
from ...services.validator import ALLOWED_DISTRICTS, ALLOWED_INDUSTRIES

router = APIRouter(prefix='/regulation', tags=['用水监管'])


@router.get('/overview')
def overview(year: int = Query(2026, ge=2020, le=2100), quarter: int = Query(3, ge=1, le=4), district: str | None = None, industry: str | None = None):
    if district is not None and district not in ALLOWED_DISTRICTS or industry is not None and industry not in ALLOWED_INDUSTRIES:
        raise HTTPException(422, '地区或行业不在当前数据范围')
    report = regulatory_inventory(year, quarter, district, industry)
    names = {unit['name'] for unit in report['all_units']}
    cases = [case for case in list_cases() if case['unit_name'] in names and case['year'] == year and case['quarter'] == quarter]
    report['cases_summary'] = {'total': len(cases), 'open': sum(case['status'] != 'closed' for case in cases),
                               'closed': sum(case['status'] == 'closed' for case in cases), 'overdue': sum(case['overdue'] for case in cases)}
    return report


@router.get('/unit')
def unit(unit_name: str = Query(min_length=1, max_length=100), year: int = Query(2026, ge=2020, le=2100), quarter: int = Query(3, ge=1, le=4)):
    dossier = unit_dossier(unit_name, year, quarter)
    if not dossier['ok']:
        raise HTTPException(404, '单位不存在')
    dossier['cases'] = list_cases(unit_name)
    return dossier


@router.get('/cases')
def cases(unit_name: str | None = Query(default=None, max_length=100)):
    return {'ok': True, 'data': list_cases(unit_name)}


def execute(action, *args):
    try:
        return action(*args)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post('/cases')
def add_case(request: CaseCreate):
    return execute(create_case, request.unit_name, request.year, request.quarter, request.owner, request.due_date.isoformat(), request.note)


@router.post('/cases/{case_id}/transition')
def update_case(case_id: str, request: CaseTransition):
    return execute(transition_case, case_id, request.target, request.note, request.actor, request.version)
