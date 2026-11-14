<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ChatPanel from '../components/ChatPanel.vue'
import { budgetStyles, formatAmount, formatRate, readInspectionReport, type InspectionReport } from '../lib/waterBudget'
import { caseNames, dueInDays, regulatoryRequest, type CaseStatus, type Dossier, type RegulatoryCase } from '../lib/regulatory'
import type { ToolResult } from '../lib/chatStream'

const route = useRoute()
const year = ref(2026), quarter = ref(3), district = ref(''), industry = ref('')
const report = ref<InspectionReport | null>(null), cases = ref<RegulatoryCase[]>([])
const loading = ref(false), error = ref(''), notice = ref(''), tab = ref<'risks' | 'cases'>('risks')
const status = ref('all'), search = ref(''), caseStatus = ref('all')
const dossier = ref<Dossier | null>(null), selectedName = ref(''), detailTab = ref<'archive' | 'months' | 'cases' | 'ai'>('archive')
const detailLoading = ref(false), actionBusy = ref(false), detailError = ref(''), detailNotice = ref('')
const owner = ref('演示监管员'), dueDate = ref(dueInDays(7)), createNote = ref('')
const transitionNotes = ref<Record<string, string>>({}), transitionTargets = ref<Record<string, CaseStatus>>({})
let overviewId = 0, detailId = 0
const abort = new AbortController()
const filteredUnits = computed(() => (report.value?.all_units ?? []).filter(unit => (status.value === 'all' || unit.budget_status === status.value) && (!search.value || unit.name.includes(search.value))))
const scopedCases = computed(() => {
  const names = new Set(report.value?.all_units.map(unit => unit.name) ?? [])
  return cases.value.filter(item => item.year === year.value && item.quarter === quarter.value && names.has(item.unit_name) && (caseStatus.value === 'all' || item.status === caseStatus.value))
})
const openCases = computed(() => cases.value.filter(item => item.year === year.value && item.quarter === quarter.value && item.status !== 'closed' && report.value?.all_units.some(unit => unit.name === item.unit_name)))
const dossierCases = computed(() => dossier.value?.cases.filter(item => item.year === year.value && item.quarter === quarter.value) ?? [])
const context = computed(() => ({ available: false, selected_unit: selectedName.value || null, year: year.value, quarter: quarter.value }))

async function load() {
  const request = ++overviewId; loading.value = true; error.value = ''; report.value = null
  const query = new URLSearchParams({ year: String(year.value), quarter: String(quarter.value) })
  if (district.value) query.set('district', district.value)
  if (industry.value) query.set('industry', industry.value)
  try {
    const [data, caseData] = await Promise.all([regulatoryRequest<Record<string, unknown>>(`/overview?${query}`, { signal: abort.signal }), regulatoryRequest<{ data: RegulatoryCase[] }>('/cases', { signal: abort.signal })])
    if (request !== overviewId || abort.signal.aborted) return
    const parsed = readInspectionReport(data)
    if (!parsed) throw new Error('监管数据格式不完整')
    report.value = parsed; cases.value = caseData.data
  } catch (exc) { if (request === overviewId && !abort.signal.aborted) error.value = exc instanceof Error ? exc.message : '加载失败' }
  finally { if (request === overviewId) loading.value = false }
}
async function openUnit(name: string, nextTab: typeof detailTab.value = 'archive') {
  if (actionBusy.value) return
  selectedName.value = name; detailTab.value = nextTab; detailError.value = ''; detailNotice.value = ''; dossier.value = null; detailLoading.value = true
  const request = ++detailId
  try {
    const data = await regulatoryRequest<Dossier>(`/unit?${new URLSearchParams({ unit_name: name, year: String(year.value), quarter: String(quarter.value) })}`, { signal: abort.signal })
    if (request !== detailId || abort.signal.aborted) return
    dossier.value = data
    createNote.value = data.data.evidence?.join('\n') ?? '请核实该单位当期用水记录和有效指标。'
    for (const item of data.cases) transitionTargets.value[item.id] = item.allowed_next[0] ?? 'checking'
  } catch (exc) { if (request === detailId && !abort.signal.aborted) detailError.value = exc instanceof Error ? exc.message : '档案加载失败' }
  finally { if (request === detailId) detailLoading.value = false }
}
function closeDetail() { if (actionBusy.value) return; ++detailId; selectedName.value = ''; dossier.value = null }
async function createCase() {
  if (!dossier.value || actionBusy.value) return
  actionBusy.value = true; detailError.value = ''; detailNotice.value = ''
  try {
    const result = await regulatoryRequest<{ created: boolean }>('/cases', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ unit_name: selectedName.value, year: year.value, quarter: quarter.value, owner: owner.value, due_date: dueDate.value, note: createNote.value }) })
    detailNotice.value = result.created ? '核查待办已建立，已保存本次预警证据快照。' : '该期间同类预警已有核查记录。'
    const [updated, latestCases] = await Promise.all([regulatoryRequest<Dossier>(`/unit?${new URLSearchParams({ unit_name: selectedName.value, year: String(year.value), quarter: String(quarter.value) })}`), regulatoryRequest<{ data: RegulatoryCase[] }>('/cases')])
    dossier.value = updated; cases.value = latestCases.data; detailTab.value = 'cases'
    for (const item of updated.cases) transitionTargets.value[item.id] = item.allowed_next[0] ?? 'checking'
  } catch (exc) { detailError.value = exc instanceof Error ? exc.message : '创建失败' }
  finally { actionBusy.value = false }
}
async function advance(item: RegulatoryCase) {
  if (actionBusy.value) return
  actionBusy.value = true; detailError.value = ''; detailNotice.value = ''
  try {
    const result = await regulatoryRequest<{ case: RegulatoryCase }>(`/cases/${item.id}/transition`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target: transitionTargets.value[item.id], note: transitionNotes.value[item.id], actor: owner.value, version: item.version }) })
    cases.value = cases.value.map(value => value.id === item.id ? result.case : value)
    if (dossier.value) dossier.value.cases = dossier.value.cases.map(value => value.id === item.id ? result.case : value)
    transitionNotes.value[item.id] = ''; transitionTargets.value[item.id] = result.case.allowed_next[0] ?? 'checking'
    detailNotice.value = `已记录为${result.case.status_label}，办理历史已保存。`
  } catch (exc) { detailError.value = exc instanceof Error ? exc.message : '更新失败，请刷新后重试' }
  finally { actionBusy.value = false }
}
function onToolResult(result: ToolResult) {
  if (result.tool === 'list_regulatory_cases' && result.result.ok) notice.value = 'AI已查询办理记录；实际处理请在核查记录中操作。'
}
function followRoute() {
  const routeYear = Number(route.query.year), routeQuarter = Number(route.query.quarter)
  if (Number.isInteger(routeYear) && routeYear >= 2020 && routeYear <= 2100) year.value = routeYear
  if (Number.isInteger(routeQuarter) && routeQuarter >= 1 && routeQuarter <= 4) quarter.value = routeQuarter
  if (typeof route.query.unit === 'string') void openUnit(route.query.unit, route.query.tab === 'cases' ? 'cases' : 'archive')
}
function selectPeriod() { closeDetail(); void load() }
onMounted(() => { followRoute(); void load() })
watch(() => route.query, followRoute)
onBeforeUnmount(() => { ++overviewId; ++detailId; abort.abort() })
</script>

<template>
  <div class="regulation-page">
    <div class="page-heading"><div><span class="eyebrow">执行监测 · 预警核查 · 整改复核</span><h1>用水监管工作台</h1><p>先核验统计口径，再看执行风险，把需要处理的预警转成核查待办。</p></div><RouterLink class="primary-link" :to="{ path: '/map', query: { year, quarter } }">在地图上查看 ↗</RouterLink></div>
    <div class="filters"><label>年度<select v-model.number="year" :disabled="actionBusy" @change="selectPeriod"><option :value="2025">2025</option><option :value="2026">2026</option><option :value="2027">2027</option></select></label><label>累计至<select v-model.number="quarter" :disabled="actionBusy" @change="selectPeriod"><option v-for="q in 4" :key="q" :value="q">第 {{ q }} 季度末</option></select></label><label>管辖区<select v-model="district" @change="load"><option value="">全部区县</option><option v-for="value in ['通州区', '大兴区', '朝阳区', '顺义区']" :key="value">{{ value }}</option></select></label><label>行业<select v-model="industry" @change="load"><option value="">全部行业</option><option v-for="value in ['制造业', '服务业', '农业', '建筑业']" :key="value">{{ value }}</option></select></label><button type="button" :disabled="loading || actionBusy" @click="load">刷新</button></div>
    <div v-if="report" class="data-basis"><strong>{{ report.period?.label }}</strong><span>口径：{{ report.period?.comparison }} · 水量单位：立方米</span><span v-if="report.demo_mode" class="demo-tag">演示档案与计量 · 截至 2026-09-30</span></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" class="message" role="status">{{ notice }}</p>
    <div v-if="loading" class="empty">正在核验档案、有效指标和计量记录…</div>
    <template v-if="report">
      <div class="metrics"><button type="button" @click="tab='risks';status='all'"><span>管理单位</span><b>{{ report.summary.checked_count }}</b><small>所选辖区与行业</small></button><button class="red" type="button" @click="tab='risks';status='over_budget'"><span>已超年度指标</span><b>{{ report.summary.over_budget }}</b><small>其中 {{ report.summary.inspection_required ?? 0 }} 家超用超过20%</small></button><button class="amber" type="button" @click="tab='risks';status='near_limit'"><span>预计超年度指标</span><b>{{ report.summary.forecast_risk ?? 0 }}</b><small>按季节分配进度外推</small></button><button class="gray" type="button" @click="tab='risks';status='invalid_data'"><span>数据待核实</span><b>{{ report.summary.invalid_data }}</b><small>指标待下达 {{ report.summary.data_pending_reasons?.indicator_pending ?? 0 }} · 月报问题 {{ report.summary.data_pending_reasons?.missing_monthly ?? 0 }} · 其他 {{ report.summary.data_pending_reasons?.other ?? 0 }}</small></button><button class="blue" type="button" @click="tab='cases';caseStatus='all'"><span>未办结核查</span><b>{{ openCases.length }}</b><small>{{ openCases.filter(item => item.overdue).length }} 条已超办理期限</small></button></div>
      <div class="business-note"><strong>预警依据</strong><span>已发生超用与预测风险分开处理。北京案例：年度超指标严格超过20%建议监督检查；预测只作提醒，不能作为违法认定。</span><a href="https://www.beijing.gov.cn/zhengce/zhengcefagui/202310/t20231030_3290091.html" target="_blank" rel="noopener noreferrer">查看政策依据 ↗</a></div>
      <section class="list-card"><div class="list-head"><div class="tabs"><button :class="{active:tab==='risks'}" @click="tab='risks'">执行与预警</button><button :class="{active:tab==='cases'}" @click="tab='cases'">核查待办</button></div><div v-if="tab==='risks'" class="list-filters"><select v-model="status"><option value="all">全部状态</option><option v-for="(style,key) in budgetStyles" :key="key" :value="key">{{ style.label }}</option></select><input v-model="search" placeholder="搜索单位名称" aria-label="搜索单位名称"></div><select v-else v-model="caseStatus"><option value="all">全部办理状态</option><option v-for="(name,key) in caseNames" :key="key" :value="key">{{ name }}</option></select></div>
        <div v-if="tab==='risks'" class="table-scroll"><table><thead><tr><th>单位与口径</th><th>监管状态</th><th>累计用水</th><th>年度指标</th><th>执行比例</th><th>预计全年</th><th>操作</th></tr></thead><tbody><tr v-for="unit in filteredUnits" :key="unit.name"><td><button class="text-link unit-name" @click="openUnit(unit.name)">{{ unit.name }}</button><small>{{ unit.district }} · {{ unit.industry }} · {{ unit.water_source ?? '水源待核实' }}</small></td><td><span class="status-pill" :style="{color:budgetStyles[unit.budget_status].color}">{{ unit.status_label }}</span><small v-if="unit.inspection_required">建议监督检查</small></td><td>{{ formatAmount(unit.water_used) }}<small v-if="unit.data_issues?.length">已记录数值，口径待核实</small></td><td>{{ formatAmount(unit.budget) }}<small>{{ unit.indicator_state==='issued' ? '有效版本 '+unit.indicator_version : '指标未下达或缺失' }}</small></td><td>{{ formatRate(unit) }}</td><td>{{ formatAmount(unit.forecast_annual ?? null) }}<small v-if="unit.forecast_annual">情景预测</small></td><td><button class="text-link" @click="openUnit(unit.name)">查看档案</button><button v-if="unit.budget_status!=='normal'" class="text-link" @click="openUnit(unit.name,'cases')">建立核查</button></td></tr></tbody></table><p v-if="!filteredUnits.length" class="empty">该范围或筛选状态下没有单位。</p></div>
        <div v-else class="table-scroll"><table><thead><tr><th>单位</th><th>统计期间</th><th>办理状态</th><th>责任人</th><th>办理期限</th><th>操作</th></tr></thead><tbody><tr v-for="item in scopedCases" :key="item.id"><td>{{ item.unit_name }}</td><td>{{ item.year }} · 截至Q{{ item.quarter }}</td><td><span class="status-pill">{{ item.status_label }}</span></td><td>{{ item.owner }}</td><td :class="{error:item.overdue}">{{ item.due_date }}<small v-if="item.overdue">已逾期</small></td><td><button class="text-link" @click="openUnit(item.unit_name,'cases')">办理与历史</button></td></tr></tbody></table><p v-if="!scopedCases.length" class="empty">暂无核查记录。从预警单位建立待办后，将在这里持续跟踪。</p></div>
      </section><p class="footnote">{{ report.note }} 行业定额尚未接入，暂不提供用水效率合规结论。</p>
    </template>
    <div v-if="selectedName" class="drawer-backdrop" @click.self="closeDetail"><aside class="unit-drawer" aria-label="单位档案与核查"><header><div><span class="eyebrow">一户一档 · {{ year }} / 截至Q{{ quarter }}</span><h2>{{ selectedName }}</h2></div><button type="button" :disabled="actionBusy" aria-label="关闭档案" @click="closeDetail">×</button></header><nav class="detail-tabs"><button v-for="(label,key) in {archive:'单位档案',months:'月度计量',cases:'核查记录',ai:'AI分析'}" :key="key" :class="{active:detailTab===key}" :disabled="actionBusy" @click="detailTab=key">{{ label }}</button></nav><p v-if="detailError" class="error" role="alert">{{ detailError }}</p><p v-if="detailNotice" class="message" role="status">{{ detailNotice }}</p><p v-if="detailLoading" class="empty">正在读取档案…</p>
      <div v-if="detailTab==='ai'" class="detail-ai"><ChatPanel :map-context="context" @tool-result="onToolResult" /></div>
      <div v-else-if="dossier" class="detail-body">
        <template v-if="detailTab==='archive'"><div class="risk-heading"><span class="status-pill" :style="{color:budgetStyles[dossier.data.budget_status].color}">{{ dossier.data.status_label }}</span><RouterLink class="text-link" :to="{path:'/map',query:{unit:selectedName,year,quarter}}">地图定位 ↗</RouterLink></div><h3>预警证据</h3><ul class="evidence"><li v-for="line in dossier.data.evidence" :key="line">{{ line }}</li></ul><p v-if="dossier.data.forecast_method" class="footnote">{{ dossier.data.forecast_method }}</p>
          <template v-if="dossier.archive"><h3>管理与计量档案</h3><dl><div><dt>管理编号</dt><dd>{{ dossier.archive.archive_id }}</dd></div><div><dt>管理类型</dt><dd>{{ dossier.archive.management_type }}</dd></div><div><dt>管理机构</dt><dd>{{ dossier.archive.responsible_office }}</dd></div><div><dt>水源 / 用途</dt><dd>{{ dossier.archive.water_source }} / {{ dossier.archive.purpose }}</dd></div><div><dt>取水许可证</dt><dd>{{ dossier.archive.permit_id ?? '公共供水单位，不适用自备取水许可' }}</dd></div><div v-if="dossier.archive.permit_volume"><dt>许可水量</dt><dd>{{ formatAmount(dossier.archive.permit_volume) }} m³</dd></div></dl><h3>年度指标与版本</h3><dl><div><dt>下达状态</dt><dd>{{ dossier.archive.indicator.state==='issued'?'已下达':'待下达' }}</dd></div><div><dt>指标水量</dt><dd>{{ formatAmount(dossier.archive.indicator.annual_volume) }} m³</dd></div><div><dt>指标版本 / 文号</dt><dd>{{ dossier.archive.indicator.version }} / {{ dossier.archive.indicator.document_id }}</dd></div><div><dt>有效期间</dt><dd>{{ dossier.archive.indicator.effective_from }} 至 {{ dossier.archive.indicator.effective_to }}</dd></div><div><dt>核定依据</dt><dd>{{ dossier.archive.indicator.method }}</dd></div></dl><h3>户—表关系</h3><div v-for="meter in dossier.archive.meters" :key="meter.id" class="meter">{{ meter.id }} · {{ meter.level }} · {{ meter.source }}</div><h3>水效核算所需资料</h3><p>{{ dossier.archive.scale.metric }}：{{ dossier.archive.scale.value }} {{ dossier.archive.scale.unit }}</p><p class="footnote">{{ dossier.archive.scale.note }}</p></template><p v-else class="empty">未关联完整周期档案，请先核实数据。</p>
        </template>
        <template v-else-if="detailTab==='months'"><p class="footnote">按单位总表统计；仅展示所选累计期间，缺报不自动补零。</p><table><thead><tr><th>月份</th><th>用水量（m³）</th><th>计量表</th><th>数据状态</th></tr></thead><tbody><tr v-for="month in quarter*3" :key="month"><td>{{ year }}-{{ String(month).padStart(2,'0') }}</td><td>{{ formatAmount(dossier.archive?.indicator.year===year ? dossier.archive.monthly.find(row=>row.month===month)?.volume ?? null : null) }}</td><td>{{ dossier.archive?.indicator.year===year ? dossier.archive.monthly.find(row=>row.month===month)?.meter_id ?? '—' : '—' }}</td><td>{{ dossier.archive?.indicator.year===year && dossier.archive.monthly.find(row=>row.month===month)?.quality==='verified' ? '演示已核验' : '缺报 / 待核实' }}</td></tr></tbody></table></template>
        <template v-else-if="detailTab==='cases'"><p class="footnote">办理记录保存在本地演示台账。填写人为操作人记录，当前未接入正式身份认证和行政审批。</p><div v-if="dossier.data.budget_status!=='normal'" class="case-form"><h3>建立当期核查待办</h3><label>责任人 / 记录人<input v-model="owner" maxlength="50" :disabled="actionBusy"></label><label>办理期限<input v-model="dueDate" type="date" :min="dueInDays(0)" :disabled="actionBusy"></label><label>核查事项<textarea v-model="createNote" rows="4" maxlength="1000" :disabled="actionBusy"></textarea></label><button class="primary-button" :disabled="actionBusy || !owner.trim() || !dueDate || createNote.trim().length<5" @click="createCase">{{ actionBusy?'保存中…':'建立核查待办' }}</button></div><p v-if="!dossierCases.length" class="empty">当前期间暂无办理记录。</p>
          <article v-for="item in dossierCases" :key="item.id" class="case-card"><div class="risk-heading"><strong>{{ item.status_label }}</strong><span :class="{error:item.overdue}">{{ item.owner }} · {{ item.due_date }}{{ item.overdue?' · 逾期':'' }}</span></div><details><summary>建单时的预警证据</summary><ul class="evidence"><li v-for="line in item.snapshot.evidence" :key="line">{{ line }}</li></ul></details><ol class="timeline"><li v-for="event in item.events" :key="event.id"><strong>{{ caseNames[event.to_status] }}</strong><small>{{ event.actor }} · {{ event.created_at }}</small><p>{{ event.note }}</p></li></ol><div class="transition-form"><label>下一步<select v-model="transitionTargets[item.id]" :disabled="actionBusy"><option v-for="next in item.allowed_next" :key="next" :value="next">{{ item.status==='closed' ? '重新核查' : caseNames[next] }}</option></select></label><label>{{ transitionTargets[item.id]==='closed'?'复核结论及办结依据':'核查发现 / 整改措施 / 复核说明' }}<textarea v-model="transitionNotes[item.id]" rows="3" maxlength="2000" :disabled="actionBusy"></textarea></label><button class="primary-button" :disabled="actionBusy || !owner.trim() || (transitionNotes[item.id]?.trim().length ?? 0)<5" @click="advance(item)">记录{{ item.status==='closed'?'重新核查':caseNames[transitionTargets[item.id] ?? 'checking'] }}</button><p class="footnote">状态变更保留历史；办结必须先经过核查和复核。</p></div></article>
        </template>
      </div>
    </aside></div>
  </div>
</template>

<style scoped>
.regulation-page { height:100%; overflow:auto; padding:28px 32px; box-sizing:border-box; color:#344054; background:#f5f7fb; font-family:"Microsoft YaHei",sans-serif; }
.page-heading { display:flex; justify-content:space-between; align-items:center; gap:20px; } .eyebrow { color:#8793a7; font-size:11px; letter-spacing:.5px; }
h1 { margin:8px 0; font-size:25px; color:#233451; font-weight:600; } .page-heading p { font-size:13px; color:#7b889e; margin:0; line-height:1.8; }
button,input,select,textarea { font:inherit; } button { cursor:pointer; } button:disabled { cursor:default; opacity:.5; } a { text-decoration:none; } button:focus-visible,a:focus-visible { outline:2px solid #4d6bfe; outline-offset:3px; }
.primary-link,.primary-button { color:#fff; background:#4d6bfe; padding:10px 14px; border:0; border-radius:8px; font-size:12px; flex-shrink:0; }
.filters { display:flex; align-items:center; flex-wrap:wrap; gap:12px; margin-top:24px; padding:14px 18px; border:1px solid #e9edf5; background:#fff; border-radius:12px; font-size:12px; }
.filters label { display:flex; align-items:center; gap:9px; color:#748096; } input,select,textarea { border:1px solid #dfe5ef; border-radius:7px; background:#fff; color:#344054; padding:8px 10px; font-size:12px; box-sizing:border-box; }
.filters button { margin-left:auto; background:#f4f6fb; border:0; border-radius:7px; padding:8px 14px; color:#526789; }
.data-basis { display:flex; flex-wrap:wrap; gap:8px 16px; align-items:center; margin:15px 0; font-size:11px; color:#7b889e; } .data-basis strong { color:#526789; font-weight:500; } .demo-tag { border-radius:5px; background:#eaf0ff; color:#6679b1; padding:4px 7px; }
.metrics { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:14px; margin:16px 0; } .metrics button { display:flex; flex-direction:column; align-items:flex-start; padding:20px; border-radius:12px; border:1px solid #e9edf5; background:#fff; color:#344054; text-align:left; }
.metrics span { font-size:12px; } .metrics b { font-size:31px; font-weight:600; margin:10px 0; } .metrics small { color:#8a95a7; font-size:10px; line-height:1.6; } .metrics .red b { color:#d65a60; } .metrics .amber b { color:#d29638; } .metrics .gray b { color:#8b96aa; } .metrics .blue b { color:#4d6bfe; }
.business-note { display:flex; align-items:center; flex-wrap:wrap; gap:8px 14px; border:1px solid #e0e7f5; background:#eef3fd; border-radius:9px; padding:12px 15px; font-size:11px; line-height:1.8; color:#6c7b95; } .business-note strong { color:#526789; } .business-note a { color:#4d6bfe; margin-left:auto; }
.list-card { background:#fff; border:1px solid #e9edf5; border-radius:12px; margin-top:20px; overflow:hidden; } .list-head { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:16px 18px; border-bottom:1px solid #edf0f5; }
.tabs,.detail-tabs { display:flex; gap:18px; } .tabs button,.detail-tabs button { padding:8px 0; background:transparent; border:0; color:#8793a7; font-size:13px; } .tabs .active,.detail-tabs .active { color:#4d6bfe; box-shadow:0 2px #4d6bfe; } .list-filters { display:flex; gap:10px; }
.table-scroll { overflow:auto; } table { width:100%; border-collapse:collapse; font-size:12px; white-space:nowrap; } th { background:#fafbfe; color:#8b95a7; font-weight:500; padding:13px 16px; text-align:left; } td { padding:15px 16px; border-top:1px solid #f0f2f7; font-variant-numeric:tabular-nums; } td small { display:block; color:#98a1b1; font-size:10px; margin-top:6px; } .text-link { border:0; background:transparent; color:#4d6bfe; padding:3px 0; margin-right:12px; font-size:12px; } .unit-name { color:#344054; font-weight:500; }
.status-pill { display:inline-block; background:#f5f7fb; border-radius:6px; padding:5px 8px; font-size:11px; } .empty { text-align:center; padding:30px 16px; color:#96a1b1; font-size:13px; } .footnote { color:#8b95a7; font-size:11px; line-height:1.9; } .error { color:#d45858; font-size:12px; line-height:1.8; } .message { color:#4c876d; font-size:12px; line-height:1.8; }
.drawer-backdrop { position:fixed; inset:0; background:rgba(22,38,65,.25); z-index:110; display:flex; justify-content:flex-end; } .unit-drawer { width:min(660px,100%); height:100%; background:#fff; display:flex; flex-direction:column; box-shadow:-10px 0 40px #1e35571a; }
.unit-drawer>header { padding:24px; display:flex; justify-content:space-between; gap:15px; } h2 { font-size:19px; color:#233451; margin:7px 0 0; } .unit-drawer>header>button { border:0; background:#f3f5f8; border-radius:8px; width:30px; height:30px; color:#8491a5; font-size:22px; } .detail-tabs { padding:0 24px 12px; border-bottom:1px solid #edf0f5; } .unit-drawer>.error,.unit-drawer>.message { padding:0 24px; }
.detail-body { flex:1; min-height:0; overflow:auto; padding:22px 24px; font-size:12px; } .detail-ai { flex:1; min-height:0; } h3 { font-size:13px; margin:22px 0 12px; color:#526789; } .risk-heading { display:flex; justify-content:space-between; align-items:center; gap:10px; font-size:11px; } .evidence { padding-left:20px; line-height:1.9; color:#6c7890; } .evidence li { margin:7px 0; }
dl { margin:0; } dl>div { display:flex; gap:15px; border-bottom:1px solid #f0f2f6; padding:10px 0; } dt { width:110px; flex-shrink:0; color:#8b95a7; } dd { margin:0; overflow-wrap:anywhere; line-height:1.8; } .meter { background:#f5f7fb; padding:11px; border-radius:8px; color:#77849b; }
.case-form,.case-card { padding:16px; background:#f8faff; border:1px solid #e4eaf6; border-radius:10px; margin:0 0 16px; } .case-form h3 { margin-top:0; } .case-form label,.transition-form label { display:flex; flex-direction:column; gap:7px; margin-bottom:12px; color:#7b889e; } textarea { resize:vertical; width:100%; line-height:1.8; } .timeline { list-style:none; padding:0 0 0 12px; border-left:2px solid #e2e9f5; margin:20px 0; } .timeline li { margin:16px 0; } .timeline small { display:block; margin:6px 0; color:#8b95a7; font-size:10px; } .timeline p { white-space:pre-wrap; line-height:1.8; color:#6c7890; } details { color:#7b889e; margin:14px 0; } summary { cursor:pointer; }
@media(max-width:1200px) { .regulation-page {padding:20px;} .metrics {gap:8px;} .metrics button {padding:14px;} }
@media(max-width:800px) { .metrics {grid-template-columns:repeat(2,minmax(0,1fr));} .page-heading,.list-head {align-items:flex-start;flex-direction:column;} .list-filters {flex-wrap:wrap;} }
</style>
