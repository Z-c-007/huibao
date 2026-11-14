import assert from 'node:assert/strict'
import { loadTs } from './test-support.mjs'
const { readAttachment } = loadTs('./src/lib/reportDownload.ts')
const data = { filename: '报告', markdown: '正文', csv: '数据', report_id: 'a'.repeat(32), version: 3, latest_version: 4 }
assert.equal(readAttachment(data).version, 3)
assert.equal(readAttachment(data).latest_version, 4)
assert.equal(readAttachment({ ...data, report_id: '../export' }).report_id, undefined)
assert.equal(readAttachment({ ...data, version: -1 }).report_id, undefined)
assert.equal(readAttachment({ ...data, version: '3' }).report_id, undefined)
assert.equal(readAttachment({ ...data, markdown: null }), null)
console.log('Passed: saved report identity/version validation and legacy attachment compatibility.')
