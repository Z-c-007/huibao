<script setup lang="ts">
import { ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { downloadReport, readAttachment, type ReportAttachment } from '../lib/reportDownload'

const props = defineProps<{ report: ReportAttachment; busy?: boolean }>()
const emit = defineEmits<{ select: [report: ReportAttachment]; revise: [report: ReportAttachment, prompt: string] }>()
const current = ref(props.report)
const preview = ref(false)
const working = ref(false)
const error = ref('')
const versions = ref<{ version: number; instruction: string; parent_version: number | null }[]>([])
watch(() => props.report, value => {
  if (value.report_id !== current.value.report_id || value.latest_version !== current.value.latest_version) versions.value = []
  current.value = value
})
function html() { return DOMPurify.sanitize(marked.parse(current.value.markdown, { async: false }) as string) }
async function load(version?: number) {
  if (!current.value.report_id) return
  working.value = true; error.value = ''
  try {
    const response = await fetch(`/api/reports/${current.value.report_id}${version ? '?version=' + version : ''}`)
    if (!response.ok) throw new Error('报告读取失败，请重试。')
    const data = await response.json()
    const report = readAttachment(data.report)
    if (!report) throw new Error('报告格式不完整。')
    current.value = report; versions.value = data.versions
    emit('select', report)
  } catch (e) { error.value = e instanceof Error ? e.message : '读取失败' }
  finally { working.value = false }
}
async function download(format: 'docx' | 'pdf' | 'csv' | 'markdown') {
  working.value = true; error.value = ''
  try { await downloadReport(current.value, format) }
  catch (e) { error.value = e instanceof Error ? e.message : '导出失败' }
  finally { working.value = false }
}
function changeVersion(event: Event) { void load(Number((event.target as HTMLSelectElement).value)) }
</script>

<template>
  <section class="report-card" aria-label="汇总报告">
    <div class="report-heading"><strong>{{ current.title || '用水执行巡查简报' }}</strong><span v-if="current.version">V{{ current.version }}</span></div>
    <p class="report-meta">{{ current.report_id ? '稿件已保存 · 可通过对话继续修改' : '巡查结果已生成' }}<br>{{ current.generated_at.replace('T', ' ').slice(0, 19) }}</p>
    <p v-if="current.latest_version && current.version && current.version < current.latest_version" class="footnote">正在查看旧稿 V{{ current.version }}，最新稿为 V{{ current.latest_version }}；继续修改会以所选旧稿为基础保存新版本。</p>
    <p v-if="current.instruction && current.version !== 1" class="revision-note">本轮要求：{{ current.instruction }}</p>
    <div class="actions">
      <button type="button" :disabled="working" @click="preview = !preview">{{ preview ? '收起正文' : '预览正文' }}</button>
      <button v-if="current.report_id" type="button" :disabled="busy || working" @click="emit('select', current)">继续对话修改</button>
      <button v-if="current.report_id" type="button" :disabled="busy || working" @click="load(current.version)">历史版本</button>
    </div>
    <label v-if="versions.length" class="version-picker">选择版本
      <select :value="current.version" :disabled="busy || working" @change="changeVersion"><option v-for="item in versions" :key="item.version" :value="item.version">V{{ item.version }} · {{ item.instruction.slice(0, 36) }}{{ item.parent_version ? `（基于 V${item.parent_version}）` : '' }}</option></select>
    </label>
    <div v-if="preview" class="report-preview" v-html="html()"></div>
    <div v-if="current.report_id" class="quick-edits">
      <button type="button" :disabled="busy || working" @click="emit('revise', current, '把当前报告改成给领导看的精简汇总，突出监督检查建议对象，保留统计和口径，去掉单位清单及逐项证据。')">精简给领导看</button>
      <button type="button" :disabled="busy || working" @click="emit('revise', current, '调整当前报告，突出已超指标、预测风险和数据待核实的分别处理建议，保留完整单位清单与逐项证据。')">完善核查建议</button>
    </div>
    <div class="actions downloads">
      <button v-if="current.report_id" class="primary" type="button" :disabled="working" @click="download('docx')">下载 Word</button>
      <button v-if="current.report_id" class="primary" type="button" :disabled="working" @click="download('pdf')">下载 PDF</button>
      <button type="button" :disabled="working" @click="download('csv')">单位清单 CSV</button>
      <button type="button" :disabled="working" @click="download('markdown')">Markdown</button>
    </div>
    <p class="footnote">导出当前所选版本；统计来自生成时的快照，重新取数需另行生成报告。</p>
    <p v-if="working" class="footnote" role="status">正在处理…</p><p v-if="error" class="error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.report-card { margin:14px 0; padding:15px; border:1px solid #e1e6f0; border-radius:12px; background:#fbfcff; font-size:12px; }
.report-heading { display:flex; gap:8px; align-items:center; }.report-heading strong { font-size:14px; }.report-heading span { background:#eef1ff; padding:3px 6px; border-radius:5px; color:#4d6bfe; }
.report-meta,.footnote { color:#9298a5; line-height:1.7; margin:7px 0; font-size:11px; }.revision-note { color:#6c7484; line-height:1.7; overflow-wrap:anywhere; }
.actions,.quick-edits { display:flex; flex-wrap:wrap; gap:7px; margin-top:10px; }.quick-edits { padding-top:10px; border-top:1px solid #edf0f5; }
button { font:inherit; background:#fff; color:#59657c; border:1px solid #dfe5ef; border-radius:7px; padding:7px 9px; cursor:pointer; }button:hover { border-color:#98a9ff; color:#4d6bfe; }button:disabled { opacity:.5; cursor:default; }button.primary { color:#4d6bfe; border-color:#ccd6ff; background:#f5f7ff; }button:focus-visible,select:focus-visible { outline:2px solid #4d6bfe; outline-offset:2px; }
.version-picker { display:block; margin-top:12px; color:#727b8d; }select { width:100%; margin-top:5px; padding:6px; border:1px solid #dfe5ef; border-radius:6px; color:#59657c; background:white; font:inherit; }
.report-preview { max-height:480px; overflow:auto; padding:12px; margin-top:12px; background:white; border:1px solid #edf0f5; border-radius:8px; font-size:12px; line-height:1.8; overflow-wrap:anywhere; }
.report-preview :deep(h1) { font-size:18px; }.report-preview :deep(h2) { font-size:15px; }.report-preview :deep(h3) { font-size:13px; }.report-preview :deep(table) { display:block; overflow:auto; border-collapse:collapse; font-size:11px; }.report-preview :deep(td),.report-preview :deep(th) { border:1px solid #ddd; padding:6px; }.report-preview :deep(ul) { padding-left:20px; }.error { color:#c94b4b; }
</style>
