export interface ReportAttachment { filename: string; markdown: string; csv: string; generated_at: string; title?: string; report_id?: string; version?: number; latest_version?: number; instruction?: string }
export function readAttachment(value: unknown): ReportAttachment | null {
  if (!value || typeof value !== 'object') return null
  const data = value as Record<string, unknown>
  if (typeof data.filename !== 'string' || typeof data.markdown !== 'string' || typeof data.csv !== 'string') return null
  const saved = typeof data.report_id === 'string' && /^[a-f0-9]{32}$/.test(data.report_id) && Number.isInteger(data.version) && Number(data.version) >= 1
  return { filename: data.filename.replace(/[\\/:*?"<>|\x00-\x1f]/g, '_').slice(0, 150) || '用水预算巡查', markdown: data.markdown, csv: data.csv, generated_at: typeof data.generated_at === 'string' ? data.generated_at : '',
    ...(saved ? { report_id: data.report_id as string, version: Number(data.version), latest_version: Number(data.latest_version) || Number(data.version), title: typeof data.title === 'string' ? data.title : undefined, instruction: typeof data.instruction === 'string' ? data.instruction : undefined } : {}) }
}
export async function downloadReport(report: ReportAttachment, format: 'markdown' | 'csv' | 'docx' | 'pdf') {
  if (format === 'docx' || format === 'pdf') {
    if (!report.report_id || !report.version) throw new Error('请先重新生成报告，以启用 Word/PDF 导出。')
    const response = await fetch(`/api/reports/${report.report_id}/export/${format}?version=${report.version}`)
    if (!response.ok) throw new Error(`导出失败（HTTP ${response.status}），请重试。`)
    saveBlob(await response.blob(), report.filename + '.' + format)
    return
  }
  const content = format === 'csv' ? '\uFEFF' + report.csv : report.markdown
  const blob = new Blob([content], { type: format === 'csv' ? 'text/csv;charset=utf-8' : 'text/markdown;charset=utf-8' })
  saveBlob(blob, report.filename + (format === 'csv' ? '.csv' : '.md'))
}
function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
