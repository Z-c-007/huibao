import type { WaterUnit } from './waterBudget'

export type CaseStatus = 'pending' | 'checking' | 'rectifying' | 'review' | 'closed'
export const caseNames: Record<CaseStatus, string> = { pending: '待核查', checking: '核查中', rectifying: '整改中', review: '待复核', closed: '已办结' }
export interface RegulatoryCase {
  id: string; unit_name: string; year: number; quarter: number; risk_type: string; status: CaseStatus; status_label: string
  owner: string; due_date: string; overdue: boolean; version: number; allowed_next: CaseStatus[]; snapshot: WaterUnit
  events: { id: number; from_status: CaseStatus | null; to_status: CaseStatus; note: string; actor: string; created_at: string }[]
}
export interface UnitArchive {
  archive_id: string; management_type: string; responsible_office: string; contact: string; water_source: string; purpose: string
  permit_id: string | null; permit_volume: number | null; meters: { id: string; level: string; source: string; purpose: string }[]
  indicator: { year: number; annual_volume: number; state: string; version: string; effective_from: string; effective_to: string; approved_on: string; method: string; document_id: string }
  monthly: { month: number; volume: number | null; meter_id: string; source: string; origin: string; quality: string }[]
  scale: { metric: string; value: number; unit: string; note: string }
  history: { version: string; action: string; date: string; annual_volume: number }[]
}
export interface Dossier { ok: boolean; data: WaterUnit; archive: UnitArchive | null; cases: RegulatoryCase[]; note: string }
export async function regulatoryRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/regulation${path}`, options)
  const body = await response.json()
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `请求失败（${response.status}），请检查填写信息。`)
  return body as T
}
export function dueInDays(days: number): string {
  const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
  const date = new Date(`${today}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}
