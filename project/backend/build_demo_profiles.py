"""Build explicit fictional archives and nine months of meter data for the demo."""
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).parent
units = json.loads((ROOT / 'data/demo_water_units.json').read_text(encoding='utf-8'))
units += [dict(name='通州某制造企业', industry='制造业', water_used=12000, budget=10000),
          dict(name='大兴某制造企业', industry='制造业', water_used=15000, budget=20000),
          dict(name='朝阳某酒店', industry='服务业', water_used=3000, budget=4000),
          dict(name='顺义某农场', industry='农业', water_used=800, budget=1200)]
profiles = []
invalid_case = 0
for index, unit in enumerate(units):
    agricultural = unit['industry'] == '农业'
    # Agriculture is seasonal: 96% of its approved annual plan occurs by September.
    weights = ([2, 2, 4, 10, 15, 18, 18, 17, 10, 2, 1, 1] if agricultural
               else [8, 6, 8, 8, 8, 8, 8, 8, 8, 10, 10, 10])
    shares = [str(Decimal(value) / 100) for value in weights]
    first_nine = sum(weights[:9])
    used = Decimal(str(unit['water_used']))
    amounts = [(used * Decimal(weight) / first_nine).quantize(Decimal('.01')) for weight in weights[:9]]
    amounts[-1] += used - sum(amounts)
    source = '地下水' if agricultural else '公共供水'
    issued = unit['budget'] > 0
    budget = unit['budget'] if issued else 6000
    monthly = [dict(month=month + 1, volume=float(value), meter_id=f'DEMO-M{index + 1:03d}',
                    source=source, origin='人工演示计量记录', quality='verified') for month, value in enumerate(amounts)]
    if not issued:
        invalid_case += 1
        if invalid_case > 2:
            monthly[6]['volume'] = None
            monthly[6]['quality'] = 'missing'
            issued = True
    profiles.append(dict(
        name=unit['name'], demo=True, archive_id=f'DEMO-U{index + 1:03d}',
        management_type='取水许可管理' if agricultural else '计划用水管理',
        responsible_office=unit['name'][:2] + '区节水管理机构（演示）',
        contact='演示联络人', water_source=source, purpose='农业灌溉' if agricultural else '生产经营',
        permit_id=f'DEMO-P{index + 1:03d}' if agricultural else None,
        permit_volume=budget * 1.1 if agricultural else None,
        meters=[dict(id=f'DEMO-M{index + 1:03d}', level='单位总表', source=source, purpose='生产经营用水')],
        indicator=dict(year=2026, annual_volume=budget, version='V1', state='issued' if issued else 'pending',
                       effective_from='2026-01-01', effective_to='2026-12-31', approved_on='2026-01-15',
                       source=source, purpose='农业灌溉' if agricultural else '生产经营',
                       method='人工演示指标，非实际行政核定', monthly_shares=shares,
                       document_id=f'DEMO-PLAN-2026-{index + 1:03d}'),
        monthly=monthly, latest_month=9,
        scale=dict(metric='灌溉面积' if agricultural else '生产经营规模', value=100 + index * 10,
                   unit='亩' if agricultural else '演示规模单位',
                   note='未接入适用行业定额，不提供水效合规结论'),
        history=[dict(version='V1', action='演示指标下达', date='2026-01-15', annual_volume=budget)]))
(ROOT / 'data/demo_regulatory_profiles.json').write_text(json.dumps(profiles, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Generated {len(profiles)} fictional profiles; cutoff 2026-09-30')
