import assert from 'node:assert/strict'
import { loadTs } from './test-support.mjs'
const { readWaterUnits, readInspectionReport, formatRate } = loadTs('./src/lib/waterBudget.ts')
const unit = (used, budget, extra = {}) => ({ name: '企业', lon: 116.72, lat: 39.8, water_used: used, budget, ...extra })
assert.equal(readWaterUnits([unit(100, 100)])[0].budget_status, 'near_limit')
assert.equal(readWaterUnits([unit(120, 100)])[0].budget_status, 'over_budget')
assert.equal(readWaterUnits([unit(1, 0)])[0].budget_status, 'invalid_data')
const tiny = readWaterUnits([unit(100.004, 100, { budget_status: 'over_budget', execution_rate: 100 })])[0]
assert.equal(formatRate(tiny), '>100%')
assert.equal(readWaterUnits([unit(120, 100, { lon: NaN })]).length, 0)
assert.equal(readWaterUnits([unit(120, 100, { budget_status: 'toString' })])[0].budget_status, 'over_budget')
const original = readWaterUnits([unit(120, 100, { district: '通州区', street: '新华街道' })])
assert.equal(readWaterUnits([unit(120, 100)], original)[0].district, '通州区')
assert.equal(readInspectionReport({ ok: true, data: [], summary: { checked_count: NaN } }), null)
const empty = readInspectionReport({ ok: true, data: [], summary: { checked_count: 0, displayed_count: 0 }, scope: { district: '通州区', industry: '建筑业' } })
assert.deepEqual(empty.data, [])
assert.equal(empty.scope.industry, '建筑业')
assert.equal(empty.demo_mode, false)
assert.equal(readInspectionReport({ ok: true, data: [], summary: { checked_count: 0 }, demo_mode: true }).demo_mode, true)
const pending = readWaterUnits([unit(80, 100, { budget_status: 'invalid_data', execution_rate: null, over_budget_amount: null, status_label: '指标尚未下达', data_issues: ['待核实'], regulatory_status: 'data_pending' })])[0]
assert.equal(pending.execution_rate, null)
assert.equal(pending.over_budget_amount, null)
assert.equal(pending.status_label, '指标尚未下达')
assert.deepEqual(pending.data_issues, ['待核实'])
const forecast = readWaterUnits([unit(65, 100, { budget_status: 'near_limit', regulatory_status: 'forecast_risk', execution_rate: 65, forecast_annual: 110 })])[0]
assert.equal(forecast.budget_status, 'near_limit')
assert.equal(forecast.forecast_annual, 110)
console.log('Passed: budget thresholds, invalid budget/coordinates, rounded overruns, prototype values, nearby membership and empty inspection.')
