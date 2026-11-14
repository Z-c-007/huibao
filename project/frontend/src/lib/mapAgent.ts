import { readWaterUnits, type BudgetStatus, type WaterUnit } from './waterBudget'
import type { AreaSelection, Coordinate } from './polygon'
export interface MapContext { available: boolean; selected_unit?: string | null; area?: AreaSelection | null; year?: number; quarter?: number }
export type UnitFilter = BudgetStatus | 'all' | 'attention'
export type MapAction = { action: 'locate_unit'; unit: WaterUnit }
  | { action: 'set_layer'; layer: 'rivers' | 'water_users'; visible: boolean }
  | { action: 'filter_units'; status: UnitFilter }
  | { action: 'reset_map' }
export function filterUnits(units: WaterUnit[], filter: UnitFilter): WaterUnit[] {
  return units.filter(unit => filter === 'all' || (filter === 'attention' ? unit.budget_status !== 'normal' : unit.budget_status === filter))
}
export function readMapAction(value: Record<string, unknown>): MapAction | null {
  if (value.ok !== true) return null
  if (value.action === 'locate_unit') {
    const unit = readWaterUnits(value.data)[0]
    return unit ? { action: 'locate_unit', unit } : null
  }
  if (value.action === 'set_layer' && (value.layer === 'rivers' || value.layer === 'water_users') && (value.visibility === 'show' || value.visibility === 'hide')) return { action: 'set_layer', layer: value.layer, visible: value.visibility === 'show' }
  if (value.action === 'filter_units' && ['all', 'attention', 'over_budget', 'near_limit', 'normal', 'invalid_data'].includes(String(value.status))) return { action: 'filter_units', status: value.status as UnitFilter }
  if (value.action === 'reset_map') return { action: 'reset_map' }
  return null
}
export function contextLabel(context?: MapContext): string {
  return [context?.year ? `${context.year}年 · 截至Q${context.quarter ?? 3}` : '', context?.selected_unit ? `当前单位：${context.selected_unit}` : '', context?.area ? `圈选区域：${context.area.coordinates.length - 1} 个顶点` : ''].filter(Boolean).join(' · ')
}
export function viewCoordinates(units: WaterUnit[], area: AreaSelection | null, priority = false): Coordinate[] {
  const targets = priority ? units.slice(0, 1) : units
  const boundary = area && (!priority || !targets.length) ? area.coordinates.slice(0, -1) : []
  return [...boundary, ...targets.map(unit => [unit.lon, unit.lat] as Coordinate)]
}
