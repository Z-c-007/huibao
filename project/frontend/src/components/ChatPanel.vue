<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowDown, ArrowUp, Check, Close, Cpu, Loading, Plus } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { readChatStream, type ChatStreamEvent, type ToolResult, type WireMessage } from '../lib/chatStream'
import { budgetStyles, formatAmount, formatRate, readInspectionReport } from '../lib/waterBudget'
import { contextLabel, type MapContext } from '../lib/mapAgent'
import { readAttachment, type ReportAttachment } from '../lib/reportDownload'
import ReportCard from './ReportCard.vue'

interface ToolStep extends ToolResult { id: string; pending: boolean }
const props = withDefaults(defineProps<{ mapLinked?: boolean; mapContext?: MapContext }>(), { mapLinked: false })
interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  reasoning: string
  thinking: boolean
  expanded: boolean
  status: 'pending' | 'done' | 'stopped' | 'error'
  phase: 'thinking' | 'tools' | 'answer'
  elapsed: number
  error?: string
  contextLabel?: string
  tools: ToolStep[]
}
const emit = defineEmits<{ (e: 'tool-result', payload: ToolResult): void; (e: 'conversation-reset'): void; (e: 'context-clear', target: 'unit' | 'area'): void }>()
const messages = ref<ChatMessage[]>([])
const input = ref('')
const deepThinking = ref(true)
const loading = ref(false)
const listRef = ref<HTMLDivElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const followScroll = ref(true)
const activeReport = ref<ReportAttachment | null>(null)
const savedOpen = ref(false)
const savedReports = ref<{ report_id: string; latest_version: number; created_at: string; scope: { district: string; industry: string } }[]>([])
const reportsError = ref('')
let history: WireMessage[] = []
let controller: AbortController | null = null
let elapsedTimer: ReturnType<typeof setInterval> | null = null
const suggestions = ['巡查当前年度截至所选季度末的用水执行，区分已超指标、预计超指标和数据待核实，说明证据。', '查看当前选中单位的档案、有效指标版本和月度计量，给出核查建议。', '生成当前范围的用水执行巡查简报，区分已发生超用与预测风险。']
const toolNames: Record<string, string> = {
  query_water_users: '查询用水单位', get_budget_status: '核查用水预算',
  find_nearby: '查询河流周边单位', get_street_ranking: '统计街道用水排行', export_full_report: '导出用水报表',
  inspect_water_budget: '执行用水预算巡查',
  locate_water_unit: '定位用水单位', set_map_layer: '调整地图图层', filter_map_units: '筛选地图单位', reset_map_view: '恢复地图总览', analyze_selected_area: '分析圈选区域', generate_inspection_report: '生成巡查简报',
  get_unit_dossier: '核验单位档案与月度计量', list_regulatory_cases: '查询核查待办与办理记录',
  get_report_draft: '读取报告稿件', revise_inspection_report: '保存报告新版本',
}
const columnNames: Record<string, string> = {
  name: '单位', industry: '行业', water_used: '实际用水', budget: '预算额度', distance_km: '距离（km）',
  lon: '经度', lat: '纬度', street: '街道', district: '区县', total_used: '总用水量', user_count: '单位数',
  execution_rate: '执行比例（%）', over_budget_amount: '超额用水', over_budget_percent: '超额比例（%）', status_label: '预算状态', id: '编号', budget_status: '状态代码',
  forecast_annual: '预计全年用水', indicator_version: '指标版本', water_source: '水源', inspection_required: '监督检查建议',
  unit_name: '单位名称', year: '年度', quarter: '截至季度', owner: '责任人', due_date: '办理期限', status: '办理状态', overdue: '是否逾期',
}
function newMessage(role: ChatMessage['role'], content = ''): ChatMessage {
  return { role, content, reasoning: '', thinking: false, expanded: true, status: 'pending', phase: 'thinking', elapsed: 0, tools: [] }
}
async function send(prompt?: string) {
  const text = (prompt ?? input.value).trim()
  if (!text || loading.value) return
  input.value = ''
  resizeInput()
  loading.value = true
  followScroll.value = true
  messages.value.push({ ...newMessage('user', text), status: 'done', contextLabel: contextLabel(props.mapContext) }, { ...newMessage('assistant'), thinking: deepThinking.value })
  const current = messages.value[messages.value.length - 1]!
  const started = performance.now()
  elapsedTimer = setInterval(() => { current.elapsed = (performance.now() - started) / 1000 }, 250)
  controller = new AbortController()
  scrollBottom()
  let lastReasoningRound = 0
  let round = 0
  const receive = (event: ChatStreamEvent) => {
    switch (event.type) {
      case 'round_start': round = event.round; current.phase = 'thinking'; break
      case 'reasoning_delta':
        if (lastReasoningRound !== round && current.reasoning) current.reasoning += '\n\n'
        lastReasoningRound = round
        current.reasoning += event.text
        current.phase = 'thinking'
        break
      case 'content_delta':
        if (current.phase !== 'answer' && current.content) current.content += '\n\n'
        current.content += event.text
        current.phase = 'answer'
        break
      case 'tool_start':
        current.phase = 'tools'
        current.tools.push({ id: event.id, tool: event.tool, args: {}, result: {}, pending: true })
        break
      case 'tool_result': {
        const step = current.tools.find((item) => item.id === event.id)
        if (step) Object.assign(step, { args: event.args, result: event.result, pending: false })
        if (event.result.ok === true) {
          const report = readAttachment(event.result.report)
          if (report?.report_id) selectReport(report, false)
        }
        emit('tool-result', { tool: event.tool, args: event.args, result: event.result })
        break
      }
      case 'done': history = event.history; current.status = 'done'; break
    }
    scrollBottom()
  }
  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history, thinking: current.thinking, map_context: props.mapContext,
        report_context: activeReport.value?.report_id ? { report_id: activeReport.value.report_id, version: activeReport.value.version } : undefined }),
    })
    if (!response.ok) throw new Error(`请求失败（HTTP ${response.status}），请稍后重试。`)
    if (!response.body) throw new Error('当前环境无法读取流式响应。')
    await readChatStream(response.body, receive)
  } catch (error) {
    if (controller.signal.aborted) current.status = 'stopped'
    else {
      current.status = 'error'
      current.error = error instanceof TypeError ? '无法连接服务，请检查网络或稍后重试。'
        : error instanceof Error ? error.message : '请求失败，请重试。'
    }
  } finally {
    current.elapsed = (performance.now() - started) / 1000
    if (elapsedTimer) clearInterval(elapsedTimer)
    elapsedTimer = null; controller = null; loading.value = false
    scrollBottom()
    nextTick(() => inputRef.value?.focus())
  }
}
function resetConversation() {
  if (loading.value) return
  messages.value = []; history = []; input.value = ''; resizeInput()
  clearReport()
  emit('conversation-reset')
}
function stopGeneration() { controller?.abort() }
function scrollBottom() {
  nextTick(() => { if (followScroll.value && listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight })
}
function onScroll() {
  const list = listRef.value
  if (list) followScroll.value = list.scrollHeight - list.scrollTop - list.clientHeight < 80
}
function resizeInput() {
  nextTick(() => {
    const element = inputRef.value
    if (!element) return
    element.style.height = 'auto'; element.style.height = `${Math.min(element.scrollHeight, 160)}px`
  })
}
function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); void send() }
}
function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text, { async: false, breaks: true }) as string)
}
function reasoningTitle(message: ChatMessage) {
  if (message.status === 'stopped') return '思考已停止'
  if (message.status === 'error') return '思考已中断'
  if (message.status === 'pending') {
    if (message.phase === 'tools') return '正在查询数据'
    if (message.phase === 'answer') return '思考完成'
    return '深度思考中'
  }
  return message.reasoning ? '已深度思考' : '本次未返回思考内容'
}
function tableRows(result: Record<string, unknown>): Record<string, unknown>[] {
  return result.ok === true && Array.isArray(result.data) ? result.data.filter((row) => row !== null && typeof row === 'object') : []
}
function tableKeys(result: Record<string, unknown>) { return Object.keys(tableRows(result)[0] ?? {}).filter(key => key in columnNames || ['forecast_annual','indicator_version','water_source','inspection_required'].includes(key)) }
function inspectionReports(message: ChatMessage) {
  return message.tools.filter(tool => ['inspect_water_budget', 'analyze_selected_area'].includes(tool.tool))
    .map(tool => readInspectionReport(tool.result)).filter(report => report !== null)
}
defineExpose({ sendPrompt: send, isBusy: loading })
function attachments(message: ChatMessage) { return message.tools.filter(tool => tool.result.ok === true && tool.tool !== 'get_report_draft').map(tool => readAttachment(tool.result.report)).filter(report => report !== null) }
function selectReport(report: ReportAttachment, focus = true) {
  activeReport.value = report
  if (report.report_id) localStorage.setItem('water-report-context', JSON.stringify({ report_id: report.report_id, version: report.version }))
  if (focus) nextTick(() => inputRef.value?.focus())
}
function clearReport() { activeReport.value = null; localStorage.removeItem('water-report-context') }
function reviseReport(report: ReportAttachment, prompt: string) { selectReport(report, false); void send(prompt) }
async function showSavedReports() {
  savedOpen.value = !savedOpen.value
  if (!savedOpen.value) return
  reportsError.value = ''
  try {
    const response = await fetch('/api/reports')
    if (!response.ok) throw new Error('已保存报告读取失败')
    savedReports.value = (await response.json()).data
  } catch (e) { reportsError.value = e instanceof Error ? e.message : '读取失败' }
}
async function openReport(reportId: string, version?: number) {
  try {
    const response = await fetch(`/api/reports/${reportId}${version ? '?version=' + version : ''}`)
    if (!response.ok) throw new Error('报告不存在或读取失败')
    const report = readAttachment((await response.json()).report)
    if (!report) throw new Error('报告数据不完整')
    selectReport(report, false)
  } catch (e) { reportsError.value = e instanceof Error ? e.message : '读取失败' }
}
onMounted(async () => {
  try {
    const cached = JSON.parse(localStorage.getItem('water-report-context') || 'null')
    if (cached && /^[a-f0-9]{32}$/.test(cached.report_id) && Number.isInteger(cached.version)) await openReport(cached.report_id, cached.version)
  } catch { clearReport() }
})
onBeforeUnmount(() => { controller?.abort(); if (elapsedTimer) clearInterval(elapsedTimer) })
</script>

<template>
  <div class="chat-panel">
    <header class="panel-head">
      <span class="brand"><span class="brand-mark">水</span>水利智能助手</span>
      <button class="saved-reports-button" type="button" :disabled="loading" @click="showSavedReports">已保存报告</button>
      <button class="new-chat" type="button" :disabled="loading" aria-label="新建对话" title="新建对话" @click="resetConversation"><el-icon><Plus /></el-icon></button>
    </header>
    <div ref="listRef" class="msg-list" @scroll="onScroll">
      <section v-if="savedOpen" class="saved-reports">
        <p v-if="reportsError" role="alert">{{ reportsError }}</p>
        <p v-if="!savedReports.length && !reportsError">暂无报告，可先在对话中生成汇总报告。</p>
        <button v-for="report in savedReports" :key="report.report_id" type="button" :disabled="loading" @click="openReport(report.report_id)">{{ report.scope.district }} · {{ report.scope.industry }} · V{{ report.latest_version }}<small>{{ report.created_at.replace('T', ' ').slice(0,19) }}</small></button>
      </section>
      <details v-if="activeReport" class="current-report"><summary>当前报告 · V{{ activeReport.version }} · {{ activeReport.title }}</summary><ReportCard :report="activeReport" :busy="loading" @select="selectReport" @revise="reviseReport" /></details>
      <div v-if="messages.length === 0" class="welcome">
        <span class="welcome-mark">水</span><h2>今天有什么可以帮您？</h2><p>核验用水档案与指标，分析执行风险，辅助监管核查。</p>
        <div class="suggestions"><button v-for="prompt in suggestions" :key="prompt" type="button" @click="send(prompt)">{{ prompt }}<span>↗</span></button></div>
      </div>
      <article v-for="(message, index) in messages" :key="index" class="msg" :class="message.role">
        <div v-if="message.role === 'user'" class="user-bubble">{{ message.content }}<div v-if="message.contextLabel" class="message-context">{{ message.contextLabel }}</div></div>
        <div v-else class="assistant-message">
          <span class="assistant-avatar" aria-hidden="true">水</span>
          <div class="assistant-body">
            <div v-if="message.thinking || message.reasoning" class="reasoning-block">
              <button class="reasoning-toggle" type="button" :aria-expanded="message.expanded" :aria-controls="`reasoning-${index}`" @click="message.expanded = !message.expanded">
                <el-icon :class="{ spinning: message.status === 'pending' && message.phase !== 'answer' }"><Loading v-if="message.status === 'pending' && message.phase !== 'answer'" /><Check v-else /></el-icon>
                <span>{{ reasoningTitle(message) }}</span><span class="elapsed">总用时 {{ message.elapsed.toFixed(1) }} 秒</span><el-icon class="chevron" :class="{ folded: !message.expanded }"><ArrowDown /></el-icon>
              </button>
              <div v-show="message.expanded" :id="`reasoning-${index}`" class="reasoning-content">
                <div v-if="message.reasoning" class="reasoning-text">{{ message.reasoning }}</div>
                <span v-else-if="message.status === 'pending'" class="waiting">正在等待思考内容<span class="dots">…</span></span>
                <span v-else class="waiting">{{ message.status === 'done' ? '模型本次未返回思考文本。' : '本次思考未完成。' }}</span>
              </div>
            </div>
            <div v-if="message.content" class="answer-content" :class="{ streaming: message.status === 'pending' && message.phase === 'answer' }" v-html="renderMarkdown(message.content)"></div>
            <div v-else-if="!message.thinking && message.status === 'pending'" class="waiting">正在处理<span class="dots">…</span></div>
            <section v-for="(report, reportIndex) in inspectionReports(message)" :key="reportIndex" class="inspection-report" aria-label="预算巡查结果">
              <div class="inspection-title">用水执行巡查完成<span>{{ report.scope.area ?? report.scope.district }} · {{ report.scope.industry }}<template v-if="report.period"><br>{{ report.period.label }} · 水量单位 m³</template></span></div>
              <div class="inspection-counts"><span>已检查 <b>{{ report.summary.checked_count }}</b> 家</span><span class="count-over">已超指标 <b>{{ report.summary.over_budget }}</b></span><span class="count-near">预计超指标 <b>{{ report.summary.forecast_risk ?? 0 }}</b></span><span>数据待核实 <b>{{ report.summary.invalid_data }}</b></span></div>
              <p v-if="report.summary.data_pending_reasons && report.summary.invalid_data" class="inspection-note">主要原因：指标待下达 {{ report.summary.data_pending_reasons.indicator_pending }} 家，月报问题 {{ report.summary.data_pending_reasons.missing_monthly }} 家，其他 {{ report.summary.data_pending_reasons.other }} 家。</p>
              <div v-if="report.data.some(unit => unit.budget_status !== 'normal')" class="inspection-list">
                <div v-for="unit in report.data.filter(unit => unit.budget_status !== 'normal')" :key="unit.name" class="inspection-unit"><span class="status-dot" :style="{ background: budgetStyles[unit.budget_status].color }"></span><div><strong>{{ unit.name }}</strong><span>{{ unit.status_label }} · 执行比例 {{ formatRate(unit) }}<template v-if="unit.budget_status === 'over_budget'"> · 超用 {{ formatAmount(unit.over_budget_amount) }} m³</template><template v-if="unit.regulatory_status==='forecast_risk'"> · 预计全年 {{ formatAmount(unit.forecast_annual ?? null) }} m³</template><template v-if="unit.inspection_required"> · 建议监督检查</template></span></div></div>
              </div>
              <p v-else class="inspection-empty">{{ report.summary.checked_count === 0 ? '该范围内没有已入库单位。' : '当前筛选下没有需要关注的单位。' }}</p>
              <div class="inspection-note">{{ props.mapLinked ? '已同步地图' : '巡查结果已生成' }} · {{ report.period ? '预测依据季节分配进度，不能视为已发生超用' : '无周期原始快照，不能判定年度风险' }}<br>{{ report.note }}</div>
            </section>
            <ReportCard v-for="attachment in attachments(message)" :key="`${attachment.report_id}-${attachment.version}`" :report="attachment" :busy="loading" @select="selectReport" @revise="reviseReport" />
            <details v-if="message.tools.length" class="tool-details">
              <summary>查询依据 · {{ message.tools.length }} 次工具调用<span v-if="message.tools.some(tool => tool.pending)" class="tool-live">执行中</span></summary>
              <div v-for="tool in message.tools" :key="tool.id" class="tool-card">
                <div class="tool-title"><span>{{ toolNames[tool.tool] ?? tool.tool }}</span><span :class="{ 'tool-error': !tool.pending && !tool.result.ok }">{{ tool.pending ? '执行中…' : tool.result.ok ? '完成' : '失败' }}</span></div>
                <template v-if="!tool.pending">
                  <div v-if="tableRows(tool.result).length" class="table-wrap"><table><thead><tr><th v-for="key in tableKeys(tool.result)" :key="key">{{ columnNames[key] ?? key }}</th></tr></thead><tbody><tr v-for="(row, rowIndex) in tableRows(tool.result)" :key="rowIndex"><td v-for="key in tableKeys(tool.result)" :key="key">{{ row[key] }}</td></tr></tbody></table></div>
                  <pre v-else>{{ JSON.stringify(tool.result, null, 2) }}</pre>
                </template>
              </div>
            </details>
            <p v-if="message.error" class="error-message" role="alert">{{ message.error }}</p><p v-if="message.status === 'stopped'" class="stopped-message">已停止生成</p>
          </div>
        </div>
      </article>
    </div>
    <div class="composer-wrap">
      <div v-if="activeReport" class="report-context">正在讨论 {{ activeReport.title }} · V{{ activeReport.version }}<button type="button" :disabled="loading" @click="clearReport">取消选择</button></div>
      <div v-if="props.mapContext?.selected_unit || props.mapContext?.area" class="context-chips">
        <span v-if="props.mapContext?.selected_unit">已选中 {{ props.mapContext.selected_unit }}<button type="button" :disabled="loading" aria-label="取消单位选择" @click="emit('context-clear', 'unit')">×</button></span>
        <span v-if="props.mapContext?.area">已圈选 {{ props.mapContext.area.coordinates.length - 1 }} 个顶点<button type="button" :disabled="loading" aria-label="清除圈选区域" @click="emit('context-clear', 'area')">×</button></span>
      </div>
      <div class="composer">
        <textarea ref="inputRef" v-model="input" rows="2" aria-label="输入问题" :placeholder="activeReport ? '说说这份报告还需要怎么调整…' : '向水利智能助手提问'" :disabled="loading" @input="resizeInput" @keydown="keydown"></textarea>
        <div class="composer-actions">
          <button class="thinking-button" :class="{ selected: deepThinking }" type="button" :aria-pressed="deepThinking" :disabled="loading" @click="deepThinking = !deepThinking"><el-icon><Cpu /></el-icon>深度思考</button>
          <button v-if="loading" class="send-button stop-button" type="button" aria-label="停止生成" title="停止生成" @click="stopGeneration"><el-icon><Close /></el-icon></button>
          <button v-else class="send-button" type="button" :disabled="!input.trim()" aria-label="发送" title="发送" @click="send()"><el-icon><ArrowUp /></el-icon></button>
        </div>
      </div>
      <div class="composer-hint">回答基于当前数据，请结合业务核实</div>
    </div>
  </div>
</template>

<style scoped>
.chat-panel { height:100%; min-height:0; display:flex; flex-direction:column; background:#fff; color:#262626; font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif; }
.saved-reports-button { margin-left:auto; margin-right:10px; border:0; background:transparent; color:#737f96; font-size:11px; padding:5px; }.saved-reports { padding:10px; background:#f7f9fd; border-radius:10px; margin-bottom:16px; font-size:12px; }.saved-reports > button { display:block; width:100%; text-align:left; padding:10px; border:0; border-bottom:1px solid #e8edf5; color:#5c6a83; background:transparent; }.saved-reports small { display:block; color:#949dac; margin-top:4px; }.current-report { font-size:12px; color:#657694; margin-bottom:15px; }.current-report > summary { cursor:pointer; }.report-context { font-size:11px; line-height:1.8; padding:6px 0 10px; color:#657694; }.report-context button { margin-left:8px; border:0; background:transparent; color:#8f99a9; font-size:11px; }
.panel-head { display:flex; align-items:center; justify-content:space-between; padding:15px 20px; border-bottom:1px solid #f0f0f0; }
.brand { display:flex; align-items:center; gap:9px; font-size:14px; font-weight:600; }
.brand-mark,.assistant-avatar,.welcome-mark { display:flex; align-items:center; justify-content:center; flex-shrink:0; color:#4d6bfe; background:#edf1ff; border-radius:10px; font-weight:600; }
.brand-mark { width:28px; height:28px; font-size:15px; }
button { font:inherit; cursor:pointer; } button:disabled { cursor:default; opacity:.5; }
button:focus-visible,textarea:focus-visible { outline:2px solid #4d6bfe; outline-offset:3px; }
.new-chat { display:grid; place-items:center; width:30px; height:30px; border:0; border-radius:7px; color:#777; background:transparent; }
.new-chat:hover { background:#f5f5f5; }
.msg-list { flex:1; min-height:0; overflow-y:auto; padding:26px 22px; scrollbar-width:thin; }
.welcome { padding:34px 0 20px; text-align:center; }
.welcome-mark { width:50px; height:50px; font-size:25px; border-radius:16px; margin:0 auto 18px; }
.welcome h2 { font-size:21px; font-weight:600; margin:0 0 10px; }
.welcome p { font-size:13px; color:#8b8b8b; line-height:1.8; margin:0 auto 25px; max-width:330px; }
.suggestions { display:flex; flex-direction:column; gap:10px; max-width:350px; margin:auto; text-align:left; }
.suggestions button { display:flex; align-items:center; justify-content:space-between; gap:10px; background:#fafafa; color:#666; border:1px solid #ededed; border-radius:12px; padding:12px 14px; font-size:13px; text-align:left; }
.suggestions button:hover { border-color:#cbd5ff; background:#f7f9ff; } .suggestions span { color:#999; }
.msg { margin-bottom:28px; } .msg.user { display:flex; justify-content:flex-end; }
.user-bubble { max-width:87%; padding:11px 16px; background:#f3f4f6; border-radius:18px; font-size:14px; line-height:1.75; white-space:pre-wrap; overflow-wrap:anywhere; }
.assistant-message { display:flex; align-items:flex-start; gap:11px; }
.assistant-avatar { width:29px; height:29px; font-size:15px; margin-top:3px; }
.assistant-body { min-width:0; flex:1; } .reasoning-block { margin:0 0 17px; }
.reasoning-toggle { display:flex; align-items:center; flex-wrap:wrap; gap:7px; max-width:100%; border:0; border-radius:8px; background:#f5f5f5; color:#686868; padding:7px 10px; font-size:12px; }
.elapsed { color:#999; font-variant-numeric:tabular-nums; } .chevron { font-size:11px; transition:transform .15s; } .chevron.folded { transform:rotate(-90deg); }
.reasoning-content { border-left:2px solid #e5e5e5; padding-left:13px; margin:13px 0 0 6px; color:#888; font-size:13px; line-height:1.85; overflow-wrap:anywhere; }
.reasoning-text { white-space:pre-wrap; } .waiting { color:#999; font-size:13px; }
.answer-content { font-size:14px; line-height:1.9; overflow-wrap:anywhere; }
.answer-content :deep(p) { margin:0 0 12px; }
.answer-content :deep(h1),.answer-content :deep(h2),.answer-content :deep(h3) { font-size:16px; margin:18px 0 10px; }
.answer-content :deep(ul),.answer-content :deep(ol) { padding-left:22px; margin:8px 0 15px; }
.answer-content :deep(pre) { overflow:auto; background:#f6f7f9; border-radius:8px; padding:12px; font-size:12px; }
.answer-content :deep(code) { background:#f3f4f6; padding:2px 4px; border-radius:4px; }
.answer-content :deep(blockquote) { border-left:3px solid #ddd; padding-left:12px; margin:12px 0; color:#777; }
.answer-content :deep(table) { display:block; max-width:100%; overflow:auto; border-collapse:collapse; margin:12px 0; font-size:12px; }
.answer-content :deep(th),.answer-content :deep(td) { border:1px solid #e6e6e6; padding:6px 9px; } .answer-content :deep(a) { color:#4d6bfe; }
.answer-content.streaming::after { content:'▍'; color:#4d6bfe; animation:blink 1s steps(2,start) infinite; }
.tool-details { margin-top:14px; color:#888; font-size:12px; } .tool-details > summary { cursor:pointer; padding:5px 0; }
.inspection-report { margin:16px 0; padding:14px; background:#f7f9ff; border:1px solid #e5ebff; border-radius:12px; }
.inspection-title { font-size:14px; font-weight:600; } .inspection-title > span { display:block; margin-top:4px; color:#888; font-size:11px; font-weight:400; }
.inspection-counts { display:flex; gap:8px 14px; flex-wrap:wrap; margin:12px 0; color:#666; font-size:12px; }
.count-over { color:#ca4747; } .count-near { color:#a76a12; }
.inspection-unit { display:flex; align-items:flex-start; gap:7px; margin:10px 0; }
.status-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; margin-top:7px; }
.inspection-unit strong { display:block; font-size:12px; font-weight:500; } .inspection-unit div > span { display:block; color:#777; font-size:11px; line-height:1.8; }
.inspection-note,.inspection-empty { margin:8px 0 0; color:#8990a2; font-size:11px; line-height:1.7; }
.tool-live { color:#4d6bfe; margin-left:8px; } .tool-card { margin:8px 0; padding:10px; border:1px solid #eee; border-radius:8px; }
.tool-title { display:flex; justify-content:space-between; gap:8px; color:#666; } .tool-error { color:#d14949; }
.table-wrap { overflow:auto; margin-top:10px; } .table-wrap table { border-collapse:collapse; font-size:11px; white-space:nowrap; }
.table-wrap th,.table-wrap td { border:1px solid #ededed; text-align:left; padding:5px 7px; }
.tool-card pre { margin:8px 0 0; white-space:pre-wrap; overflow-wrap:anywhere; font-size:11px; }
.error-message { color:#c94b4b; font-size:13px; line-height:1.7; margin:14px 0 0; } .stopped-message { color:#999; font-size:12px; margin:12px 0 0; }
.composer-wrap { padding:8px 18px 10px; } .composer { border:1px solid #e5e5e5; border-radius:20px; background:#f8f8f8; padding:13px 14px 10px; }
.composer:focus-within { border-color:#c9d2ff; }
.composer textarea { width:100%; min-height:48px; max-height:160px; resize:none; border:0; outline:none; background:transparent; color:#333; font-family:inherit; font-size:14px; line-height:1.65; box-sizing:border-box; padding:0 2px; }
.composer textarea::placeholder { color:#aaa; } .composer-actions { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-top:7px; }
.thinking-button { display:flex; align-items:center; gap:5px; border:1px solid #dedede; border-radius:16px; padding:5px 10px; background:#fff; color:#666; font-size:12px; }
.thinking-button.selected { border-color:#c9d4ff; color:#4d6bfe; background:#edf2ff; }
.send-button { display:grid; place-items:center; flex-shrink:0; width:32px; height:32px; border:0; border-radius:50%; background:#4d6bfe; color:#fff; font-size:19px; }
.send-button:disabled { background:#d2d2d2; opacity:1; } .stop-button { background:#4d6bfe; }
.composer-hint { text-align:center; font-size:11px; color:#aaa; margin-top:8px; } .spinning { animation:spin 1.5s linear infinite; } .dots { animation:blink 1.4s steps(2,start) infinite; }
@keyframes spin { to { transform:rotate(360deg); } } @keyframes blink { to { opacity:.25; } }
@media(prefers-reduced-motion:reduce) { .spinning,.dots,.answer-content.streaming::after { animation:none; } }
@media(max-width:480px) { .panel-head { padding:12px 14px; } .msg-list { padding:20px 13px; } .assistant-message { gap:8px; } .assistant-avatar { width:24px; height:24px; font-size:13px; } .composer-wrap { padding-left:12px; padding-right:12px; } }
.message-context { color:#8a93a5; font-size:11px; margin-top:6px; line-height:1.7; }
.context-chips { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
.context-chips > span { background:#f0f3ff; color:#6071b0; border-radius:8px; font-size:11px; padding:5px 8px; display:inline-flex; align-items:center; gap:8px; }
.context-chips button { border:0; background:transparent; color:inherit; padding:0 2px; font-size:15px; }
.report-attachment { margin:16px 0; border:1px solid #e5ebff; background:#f8faff; border-radius:12px; padding:14px; }
.report-attachment strong { font-size:13px; } .report-attachment p { font-size:11px; color:#8a93a5; margin:6px 0 12px; }
.report-attachment > div { display:flex; gap:8px; flex-wrap:wrap; }
.report-attachment button { background:#fff; border:1px solid #d7e0ff; border-radius:8px; padding:7px 10px; color:#4d6bfe; font-size:12px; }
</style>
