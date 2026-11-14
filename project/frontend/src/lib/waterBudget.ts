import { validatePolygon, type Coordinate } from './polygon'
export type BudgetStatus = 'over_budget' | 'near_limit' | 'normal' | 'invalid_data'
export interface ReportingPeriod { year: number; quarter: number; start: string; end: string; label: string; comparison: string; unit: string }
export interface WaterUnit {
  id?: number
  name: string
  industry: string
  district: string
  street: string
  water_used: number | null
  budget: number | null
  lon: number
  lat: number
  budget_status: BudgetStatus
  status_label: string
  execution_rate: number | null
  over_budget_amount: number | null
  over_budget_percent: number | null
  regulatory_status?: 'over_limit' | 'forecast_risk' | 'data_pending' | 'normal'
  period?: ReportingPeriod
  forecast_annual?: number | null
  forecast_over_amount?: number | null
  plan_progress_percent?: number | null
  inspection_required?: boolean
  evidence?: string[]
  data_issues?: string[]
  indicator_version?: string
  indicator_state?: string
  water_source?: string
  purpose?: string
  forecast_method?: string | null
  data_origin?: string
}
export interface InspectionReport {
  demo_mode: boolean
  period?: ReportingPeriod
  rule_mode?: string
  forecast_method?: string
  note?: string
  scope: { district: string; industry: string; area?: string }
  thresholds: { near_limit_percent: number }
  summary: { checked_count: number; displayed_count: number; over_budget: number; near_limit: number; normal: number; invalid_data: number; total_over_budget_amount: number; total_water_used?: number; total_budget?: number; totals_complete?: boolean; aggregate_execution_rate?: number | null; forecast_risk?: number; inspection_required?: number; data_pending_reasons?: { indicator_pending: number; missing_monthly: number; other: number } }
  data: WaterUnit[]
  all_units: WaterUnit[]
  area?: { type: 'Polygon'; coordinates: Coordinate[][] }
  map_view: 'overview' | 'priority'
  status_filter: string
}
export const budgetStyles: Record<BudgetStatus, { label: string; color: string }> = {
  over_budget: { label: '已超指标', color: '#e45656' },
  near_limit: { label: '预计超指标', color: '#e7a23a' },
  normal: { label: '正常', color: '#39a979' },
  invalid_data: { label: '数据待核实', color: '#8993a5' },
}
function number(value: unknown): number | null { return typeof value === 'number' && Number.isFinite(value) ? value : null }
export function formatAmount(value: number | null): string {
  return value === null ? '—' : value.toLocaleString('zh-CN', { maximumFractionDigits: 4 })
}
export function formatRate(unit: WaterUnit): string {
  if (unit.execution_rate === null) return '—'
  // Keep a small but real overrun visible instead of displaying 100% in red.
  if (unit.budget_status === 'over_budget' && unit.execution_rate <= 100) return '>100%'
  return `${unit.execution_rate.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}%`
}
export function readWaterUnits(value: unknown, fallback: WaterUnit[] = [], warningPercent = 90): WaterUnit[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item: unknown) => {
    if (!item || typeof item !== 'object') return []
    const row = item as Record<string, unknown>
    const lon = number(row.lon), lat = number(row.lat)
    if (typeof row.name !== 'string' || lon === null || lat === null || Math.abs(lon) > 180 || Math.abs(lat) > 90) return []
    const previous = fallback.find(unit => unit.name === row.name)
    const used = number(row.water_used), budget = number(row.budget)
    const valid = used !== null && used >= 0 && budget !== null && budget > 0
    const rate = valid ? used / budget * 100 : null
    const derived: BudgetStatus = rate === null ? 'invalid_data' : rate > 100 ? 'over_budget' : rate >= warningPercent ? 'near_limit' : 'normal'
    const status = typeof row.budget_status === 'string' && Object.hasOwn(budgetStyles, row.budget_status) ? row.budget_status as BudgetStatus : derived
    return [{
      id: number(row.id) ?? previous?.id, name: row.name,
      industry: typeof row.industry === 'string' ? row.industry : previous?.industry ?? '未记录',
      district: typeof row.district === 'string' ? row.district : previous?.district ?? '未归属',
      street: typeof row.street === 'string' ? row.street : previous?.street ?? '未归属',
      water_used: used, budget, lon, lat, budget_status: status, status_label: typeof row.status_label === 'string' ? row.status_label : budgetStyles[status].label,
      execution_rate: Object.hasOwn(row, 'execution_rate') ? number(row.execution_rate) : rate,
      over_budget_amount: Object.hasOwn(row, 'over_budget_amount') ? number(row.over_budget_amount) : (valid ? Math.max(used - budget, 0) : null),
      over_budget_percent: Object.hasOwn(row, 'over_budget_percent') ? number(row.over_budget_percent) : (rate === null ? null : Math.max(rate - 100, 0)),
      regulatory_status: row.regulatory_status as WaterUnit['regulatory_status'], period: row.period as ReportingPeriod | undefined,
      forecast_annual: number(row.forecast_annual), forecast_over_amount: number(row.forecast_over_amount), plan_progress_percent: number(row.plan_progress_percent),
      inspection_required: row.inspection_required === true, evidence: Array.isArray(row.evidence) ? row.evidence.filter(item => typeof item === 'string') : [],
      data_issues: Array.isArray(row.data_issues) ? row.data_issues.filter(item => typeof item === 'string') : [],
      indicator_version: typeof row.indicator_version === 'string' ? row.indicator_version : undefined,
      indicator_state: typeof row.indicator_state === 'string' ? row.indicator_state : undefined,
      water_source: typeof row.water_source === 'string' ? row.water_source : undefined, purpose: typeof row.purpose === 'string' ? row.purpose : undefined,
      forecast_method: typeof row.forecast_method === 'string' ? row.forecast_method : null,
      data_origin: typeof row.data_origin === 'string' ? row.data_origin : undefined,
    }]
  })
}
export function readInspectionReport(value: Record<string, unknown>): InspectionReport | null {
  if (value.ok !== true || !Array.isArray(value.data) || !value.summary || typeof value.summary !== 'object') return null
  const summary = value.summary as InspectionReport['summary']
  if (!Number.isFinite(summary.checked_count)) return null
  const scope = value.scope as InspectionReport['scope'] | undefined
  const thresholds = value.thresholds as InspectionReport['thresholds'] | undefined
  const warning = thresholds?.near_limit_percent ?? 90
  let area: InspectionReport['area']
  if (value.area && typeof value.area === 'object') {
    try { area = { type: 'Polygon', coordinates: [validatePolygon((value.area as { coordinates: unknown[] }).coordinates[0])] } } catch { return null }
  }
  return {
    demo_mode: value.demo_mode === true,
    period: value.period ? value.period as ReportingPeriod : undefined,
    rule_mode: typeof value.rule_mode === 'string' ? value.rule_mode : undefined,
    forecast_method: typeof value.forecast_method === 'string' ? value.forecast_method : undefined,
    note: typeof value.note === 'string' ? value.note : undefined,
    scope: scope ?? { district: '全部区县', industry: '全部行业' },
    thresholds: { near_limit_percent: warning }, summary,
    data: readWaterUnits(value.data, [], warning), all_units: readWaterUnits(value.all_units ?? value.data, [], warning), area,
    map_view: value.map_view === 'priority' ? 'priority' : 'overview',
    status_filter: typeof value.status_filter === 'string' ? value.status_filter : 'all',
  }
}
