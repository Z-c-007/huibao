<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as Cesium from 'cesium'
import { useRoute } from 'vue-router'
import { Aim, ArrowDown, ArrowRight, ChatDotRound, Close, Connection, Document, EditPen, Location, Minus, Plus, RefreshRight, Search } from '@element-plus/icons-vue'
import ChatPanel from '../components/ChatPanel.vue'
import type { ToolResult } from '../lib/chatStream'
import { budgetStyles, formatAmount, formatRate, readInspectionReport, readWaterUnits, type BudgetStatus, type InspectionReport, type WaterUnit } from '../lib/waterBudget'
import { filterUnits, readMapAction, viewCoordinates, type MapContext, type UnitFilter } from '../lib/mapAgent'
import { closePolygon, type AreaSelection, type Coordinate } from '../lib/polygon'

const containerRef = ref<HTMLDivElement>()
const route = useRoute()
const selectedYear = ref(2026), selectedQuarter = ref(3)
function routePeriod() {
  const year = Number(route.query.year), quarter = Number(route.query.quarter)
  if (Number.isInteger(year) && year >= 2020 && year <= 2100) selectedYear.value = year
  if (Number.isInteger(quarter) && quarter >= 1 && quarter <= 4) selectedQuarter.value = quarter
}
routePeriod()
const chatRef = ref<InstanceType<typeof ChatPanel>>()
const panelOpen = ref(true)
const overviewExpanded = ref(true)
const searchQuery = ref('')
const hoveredUnit = ref<WaterUnit | null>(null)
const hoverPosition = ref({ left: '0px', top: '0px' })
const inventoryLoading = ref(true)
const inventoryError = ref('')
const riverError = ref('')
const inventory = ref<InspectionReport | null>(null)
const inspection = ref<InspectionReport | null>(null)
const visibleUnits = ref<WaterUnit[]>([])
const sourceUnits = ref<WaterUnit[]>([])
const searchResults = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase()
  return query ? sourceUnits.value.filter(unit => `${unit.name} ${unit.district} ${unit.industry}`.toLocaleLowerCase().includes(query)).slice(0, 6) : []
})
const unitFilter = ref<UnitFilter>('all')
const filterNames: Record<UnitFilter, string> = { all: '全部范围内单位', over_budget: '已超年度指标', near_limit: '预计超年度指标', normal: '正常单位', invalid_data: '数据待核实', attention: '需关注的单位' }
const riversVisible = ref(true)
const unitsVisible = ref(true)
const selectedUnit = ref<WaterUnit | null>(null)
const selectedArea = ref<AreaSelection | null>(null)
const drawing = ref(false)
const drawPoints = ref<Coordinate[]>([])
const drawCursor = ref<Coordinate | null>(null)
const areaLoading = ref(false)
const mapNotice = ref('')
const mapContext = computed<MapContext>(() => ({ available: true, selected_unit: selectedUnit.value?.name ?? null, area: selectedArea.value, year: selectedYear.value, quarter: selectedQuarter.value }))
const mapMode = ref<'inventory' | 'inspection' | 'nearby'>('inventory')
const statusList: BudgetStatus[] = ['over_budget', 'near_limit', 'normal', 'invalid_data']
const currentCounts = computed(() => {
  const summary = inspection.value?.summary
  return Object.fromEntries(statusList.map(status => [status, summary?.[status] ?? sourceUnits.value.filter(unit => unit.budget_status === status).length])) as Record<BudgetStatus, number>
})
const priorityUnits = computed(() => inspection.value?.data.filter(unit => unit.budget_status !== 'normal').slice(0, 3) ?? [])
const scopeTitle = computed(() => inspection.value ? `${inspection.value.scope.area ?? inspection.value.scope.district} · ${inspection.value.scope.industry}` : mapMode.value === 'nearby' ? '河流周边查询结果' : '当前入库用水单位')
let viewer: Cesium.Viewer | null = null
let clickHandler: Cesium.ScreenSpaceEventHandler | null = null
let riverSource: Cesium.GeoJsonDataSource | null = null
let areaOutline: Cesium.Entity | null = null
let areaFill: Cesium.Entity | null = null
let drawVertices: Cesium.Entity[] = []
let areaRequest = 0
let areaAbort: AbortController | null = null
let canvas: HTMLCanvasElement | null = null
const entitiesByName = new Map<string, Cesium.Entity>()
const unitsByEntity = new Map<string, WaterUnit>()
const abort = new AbortController()
let inventoryRequest = 0
let removeCameraListener: (() => void) | undefined

onMounted(() => {
  const basemap = new Cesium.ImageryLayer(new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }), {
    saturation: 0.16, contrast: 0.78, brightness: 1.08, gamma: 1.08,
  })
  viewer = new Cesium.Viewer(containerRef.value!, {
    baseLayer: basemap,
    animation: false, timeline: false, baseLayerPicker: false, geocoder: false,
    homeButton: false, sceneModePicker: false, navigationHelpButton: false,
    fullscreenButton: false, infoBox: false, selectionIndicator: false,
  })
  viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#edf2f6')
  removeCameraListener = viewer.camera.moveStart.addEventListener(() => { hoveredUnit.value = null })
  viewer.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(116.65, 39.95, 120000),
    orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 } })
  clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  canvas = viewer.scene.canvas
  canvas.addEventListener('contextmenu', preventContextMenu)
  canvas.addEventListener('mouseleave', clearHover)
  document.addEventListener('keydown', drawKeydown)
  viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)
  clickHandler.setInputAction((event: { position: Cesium.Cartesian2 }) => {
    if (drawing.value) { addDrawPoint(event.position); return }
    const unit = pickUnit(event.position)
    if (unit) selectUnit(unit)
    else closeSelected()
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
  clickHandler.setInputAction((event: { endPosition: Cesium.Cartesian2 }) => {
    if (drawing.value) { drawCursor.value = coordinateAt(event.endPosition); hoveredUnit.value = null; return }
    const unit = unitsVisible.value ? pickUnit(event.endPosition) : undefined
    hoveredUnit.value = unit?.name !== selectedUnit.value?.name ? unit ?? null : null
    if (canvas) {
      canvas.style.cursor = unit ? 'pointer' : 'grab'
      hoverPosition.value = { left: `${Math.max(12, Math.min(event.endPosition.x + 16, canvas.clientWidth - 240))}px`, top: `${Math.max(12, Math.min(event.endPosition.y + 16, canvas.clientHeight - 94))}px` }
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)
  clickHandler.setInputAction(() => { if (drawing.value) void finishDraw() }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)
  void loadRivers()
  void loadInventory()
})

async function loadRivers() {
  const currentViewer = viewer
  try {
    const response = await fetch('/api/map/base', { signal: abort.signal })
    if (!response.ok) throw new Error('河道数据加载失败')
    const data = await response.json()
    // Only rivers are rendered; the removed district/street rectangles stay hidden.
    const source = await Cesium.GeoJsonDataSource.load(data.rivers, { stroke: Cesium.Color.fromCssColorString('#68a8d0').withAlpha(0.75), strokeWidth: 1.4 })
    if (viewer === currentViewer && viewer && !viewer.isDestroyed()) { riverSource = source; source.show = riversVisible.value; await viewer.dataSources.add(source) }
  } catch {
    if (!abort.signal.aborted) riverError.value = '河道暂未加载，单位数据仍可查询。'
  }
}
async function loadInventory() {
  const request = ++inventoryRequest
  inventoryLoading.value = true
  inventoryError.value = ''
  try {
    const response = await fetch(`/api/map/water-users?year=${selectedYear.value}&quarter=${selectedQuarter.value}`, { signal: abort.signal })
    if (!response.ok) throw new Error('用水单位加载失败，请重试。')
    const report = readInspectionReport(await response.json())
    if (!report) throw new Error('单位数据格式不完整，请重试。')
    if (request !== inventoryRequest || abort.signal.aborted) return
    inventory.value = report
    if (mapMode.value === 'inventory') {
      sourceUnits.value = report.all_units; renderFiltered(); zoomToUnits(visibleUnits.value)
      const requested = typeof route.query.unit === 'string' ? sourceUnits.value.find(unit => unit.name === route.query.unit) : undefined
      if (requested) selectUnit(requested, true)
    }
  } catch (error) {
    if (!abort.signal.aborted && request === inventoryRequest) inventoryError.value = error instanceof Error ? error.message : '数据加载失败，请重试。'
  } finally {
    if (request === inventoryRequest) inventoryLoading.value = false
  }
}
function renderUnits(units: WaterUnit[]) {
  if (!viewer || viewer.isDestroyed()) return
  for (const entity of entitiesByName.values()) viewer.entities.remove(entity)
  entitiesByName.clear(); unitsByEntity.clear()
  visibleUnits.value = units
  selectedUnit.value = null
  hoveredUnit.value = null
  for (const unit of units) {
    const entity = viewer.entities.add({
      show: unitsVisible.value,
      position: Cesium.Cartesian3.fromDegrees(unit.lon, unit.lat),
      point: { pixelSize: unit.budget_status === 'over_budget' ? 12 : 9,
        color: Cesium.Color.fromCssColorString(budgetStyles[unit.budget_status].color),
        outlineColor: Cesium.Color.WHITE, outlineWidth: 2, disableDepthTestDistance: Number.POSITIVE_INFINITY },
      label: { show: false, text: `${unit.name.replace(/（演示）$/, '')} · ${formatRate(unit)}`,
        font: '12px "Microsoft YaHei", sans-serif', fillColor: Cesium.Color.WHITE,
        showBackground: true, backgroundColor: Cesium.Color.fromCssColorString('#25354d').withAlpha(0.95),
        backgroundPadding: new Cesium.Cartesian2(11, 8), pixelOffset: new Cesium.Cartesian2(0, -26),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM, disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scaleByDistance: new Cesium.NearFarScalar(1000, 1, 300000, 0.7) },
    })
    entitiesByName.set(unit.name, entity)
    unitsByEntity.set(entity.id, unit)
  }
}
function pickUnit(position: Cesium.Cartesian2) {
  const picked = viewer?.scene.drillPick(position, 8) ?? []
  return picked.map(item => item.id instanceof Cesium.Entity ? unitsByEntity.get(item.id.id) : undefined).find(Boolean)
}
function clearHover() { hoveredUnit.value = null; if (canvas) canvas.style.cursor = '' }
function zoomToUnits(units: WaterUnit[], priority = false) {
  if (!viewer) return
  const targets = viewCoordinates(units, selectedArea.value, priority)
  if (!targets.length) return
  const sphere = Cesium.BoundingSphere.fromPoints(targets.map(point => Cesium.Cartesian3.fromDegrees(...point)))
  viewer.camera.flyToBoundingSphere(sphere, { duration: 1.2,
    offset: new Cesium.HeadingPitchRange(0, -Math.PI / 2, Math.max(sphere.radius * 3.4, priority ? 14000 : 30000)) })
}
function updateSelection() {
  for (const [name, entity] of entitiesByName) {
    const unit = unitsByEntity.get(entity.id)
    if (!entity.point || !unit) continue
    const selected = name === selectedUnit.value?.name
    entity.point.pixelSize = new Cesium.ConstantProperty(selected ? 18 : unit.budget_status === 'over_budget' ? 12 : 9)
    entity.point.outlineColor = new Cesium.ConstantProperty(selected ? Cesium.Color.fromCssColorString('#4d6bfe') : Cesium.Color.WHITE)
    entity.point.outlineWidth = new Cesium.ConstantProperty(selected ? 4 : 2)
    if (entity.label) entity.label.show = new Cesium.ConstantProperty(selected)
  }
}
function selectUnit(unit: WaterUnit, fly = false, foldOverview = true) {
  selectedUnit.value = unit
  hoveredUnit.value = null
  if (foldOverview) overviewExpanded.value = false
  updateSelection()
  if (fly) zoomToUnits([unit], true)
}
function closeSelected() { selectedUnit.value = null; hoveredUnit.value = null; overviewExpanded.value = true; updateSelection() }
function chooseSearch(unit: WaterUnit) {
  unitFilter.value = 'all'; unitsVisible.value = true; renderFiltered(); selectUnit(unit, true); searchQuery.value = ''
}
function selectStatus(status: BudgetStatus) {
  unitFilter.value = unitFilter.value === status ? 'all' : status; unitsVisible.value = true; renderFiltered()
}
function cameraZoom(direction: 'in' | 'out') {
  if (!viewer) return
  const distance = Math.max(viewer.camera.positionCartographic.height * 0.35, 500)
  if (direction === 'in') viewer.camera.zoomIn(distance)
  else viewer.camera.zoomOut(distance)
}
function showInventory(resetLayers = false) {
  clearArea()
  closeSelected()
  mapMode.value = 'inventory'
  inspection.value = null
  unitFilter.value = 'all'
  overviewExpanded.value = true; searchQuery.value = ''
  if (resetLayers) { riversVisible.value = true; unitsVisible.value = true }
  if (inventory.value) { sourceUnits.value = inventory.value.all_units; renderFiltered(); zoomToUnits(visibleUnits.value) }
  else void loadInventory()
}
function refreshInventory() {
  clearArea()
  closeSelected()
  searchQuery.value = ''
  unitFilter.value = 'all'
  mapMode.value = 'inventory'
  inspection.value = null
  void loadInventory()
}
function onToolResult(result: ToolResult) {
  if (!result.result.ok) return
  const action = readMapAction(result.result)
  if (action) {
    if (action.action === 'set_layer') {
      if (action.layer === 'rivers') riversVisible.value = action.visible
      else unitsVisible.value = action.visible
      mapNotice.value = `${action.layer === 'rivers' ? '河道' : '用水单位'}图层已${action.visible ? '显示' : '隐藏'}`
    } else if (action.action === 'filter_units') {
      unitFilter.value = action.status; unitsVisible.value = true; renderFiltered(); zoomToUnits(visibleUnits.value)
      mapNotice.value = `当前范围匹配 ${visibleUnits.value.length} 家单位`
    } else if (action.action === 'reset_map') { showInventory(true); mapNotice.value = '已恢复全库总览' }
    else if (action.action === 'locate_unit') {
      if (!sourceUnits.value.some(unit => unit.name === action.unit.name)) { showInventory(); sourceUnits.value = [...sourceUnits.value.filter(unit => unit.name !== action.unit.name), action.unit] }
      unitFilter.value = 'all'; unitsVisible.value = true; renderFiltered(); selectUnit(action.unit, true)
      mapNotice.value = `已定位 ${action.unit.name}`
    }
    return
  }
  if (['inspect_water_budget', 'analyze_selected_area'].includes(result.tool)) {
    const report = readInspectionReport(result.result)
    if (!report) return
    applyInspection(report)
  } else if (result.tool === 'find_nearby') {
    clearArea()
    mapMode.value = 'nearby'
    inspection.value = null
    const units = readWaterUnits(result.result.data, inventory.value?.data)
    sourceUnits.value = units; unitFilter.value = 'all'; unitsVisible.value = true; renderFiltered()
    zoomToUnits(units)
  }
}
function startInspection() {
  panelOpen.value = true
  void chatRef.value?.sendPrompt(`巡查${selectedYear.value}年截至第${selectedQuarter.value}季度末的全部单位，区分已超年度指标、预计超年度指标和数据待核实，列出证据和需监督检查对象，并更新地图。`)
}
function renderFiltered() {
  const selectedName = selectedUnit.value?.name
  renderUnits(filterUnits(sourceUnits.value, unitFilter.value))
  const previous = visibleUnits.value.find(unit => unit.name === selectedName)
  if (previous) selectUnit(previous, false, false)
}
function applyInspection(report: InspectionReport) {
  if (report.period) {
    const changed = report.period.year !== selectedYear.value || report.period.quarter !== selectedQuarter.value
    selectedYear.value = report.period.year; selectedQuarter.value = report.period.quarter
    if (changed) void loadInventory()
  }
  if (report.area) { selectedArea.value = { coordinates: report.area.coordinates[0]! }; drawPoints.value = selectedArea.value.coordinates.slice(0, -1); drawCursor.value = null; ensureAreaOverlay() }
  else clearArea()
  mapMode.value = 'inspection'; inspection.value = report; sourceUnits.value = report.all_units
  unitFilter.value = report.status_filter as UnitFilter; unitsVisible.value = true; renderFiltered()
  const priority = report.map_view === 'priority' ? visibleUnits.value[0] : visibleUnits.value.find(unit => unit.budget_status !== 'normal')
  if (priority) selectUnit(priority)
  zoomToUnits(visibleUnits.value, report.map_view === 'priority')
}
function askSelected() { panelOpen.value = true; void chatRef.value?.sendPrompt('分析当前选中单位的用水预算执行情况，简短给出数据依据和核查建议。') }
function askArea() { panelOpen.value = true; void chatRef.value?.sendPrompt('分析当前圈选区域的用水和预算情况，列出需要重点核查的单位，简短回答。') }
function requestReport() {
  panelOpen.value = true
  const prompt = inspection.value?.area ? '生成当前圈选区域的预算巡查简报和CSV清单，供我下载。' : inspection.value ? '生成刚才巡查范围的预算简报和CSV清单，供我下载。' : '生成全量用水预算巡查简报和CSV清单，供我下载。'
  void chatRef.value?.sendPrompt(prompt)
}
function clearContext(target: 'unit' | 'area') { if (target === 'unit') closeSelected(); else showInventory() }
function coordinateAt(position: Cesium.Cartesian2): Coordinate | null {
  if (!viewer) return null
  const ray = viewer.camera.getPickRay(position)
  const point = (ray ? viewer.scene.globe.pick(ray, viewer.scene) : undefined) ?? viewer.camera.pickEllipsoid(position, viewer.scene.globe.ellipsoid)
  if (!point) return null
  const cartographic = Cesium.Cartographic.fromCartesian(point)
  return [Cesium.Math.toDegrees(cartographic.longitude), Cesium.Math.toDegrees(cartographic.latitude)]
}
function overlayPositions() {
  const points = [...drawPoints.value]
  if (drawing.value && drawCursor.value) points.push(drawCursor.value)
  return points.map(point => Cesium.Cartesian3.fromDegrees(...point))
}
function ensureAreaOverlay() {
  if (!viewer || areaOutline) return
  areaOutline = viewer.entities.add({ polyline: { positions: new Cesium.CallbackProperty(() => {
    const points = overlayPositions(); return points.length > 2 ? [...points, points[0]!] : points
  }, false), width: 3, material: Cesium.Color.fromCssColorString('#4d6bfe'), clampToGround: true } })
  areaFill = viewer.entities.add({ polygon: { show: new Cesium.CallbackProperty(() => overlayPositions().length >= 3, false),
    hierarchy: new Cesium.CallbackProperty(() => new Cesium.PolygonHierarchy(overlayPositions()), false), material: Cesium.Color.fromCssColorString('#4d6bfe').withAlpha(0.12), height: 0 } })
}
function refreshDrawVertices() {
  if (!viewer) return
  for (const entity of drawVertices) viewer.entities.remove(entity)
  drawVertices = drawing.value ? drawPoints.value.map((point, index) => viewer!.entities.add({ position: Cesium.Cartesian3.fromDegrees(...point),
    point: { pixelSize: 9, color: Cesium.Color.fromCssColorString('#4d6bfe'), outlineColor: Cesium.Color.WHITE, outlineWidth: 2, disableDepthTestDistance: Infinity },
    label: { text: String(index + 1), font: '12px sans-serif', pixelOffset: new Cesium.Cartesian2(0, -16), fillColor: Cesium.Color.fromCssColorString('#4d6bfe'), disableDepthTestDistance: Infinity } })) : []
}
function cameraDrawing(active: boolean) { if (viewer) { const control = viewer.scene.screenSpaceCameraController; control.enableRotate = !active; control.enableTranslate = !active; control.enableTilt = !active; control.enableLook = !active } }
function startDraw() {
  if (!viewer || drawing.value || areaLoading.value || chatRef.value?.isBusy) return
  hoveredUnit.value = null; overviewExpanded.value = true
  drawing.value = true; drawPoints.value = []; drawCursor.value = null; mapNotice.value = ''; ensureAreaOverlay(); cameraDrawing(true)
}
function addDrawPoint(position: Cesium.Cartesian2) {
  if (drawPoints.value.length >= 64) { mapNotice.value = '最多添加64个顶点，请完成圈选。'; return }
  const point = coordinateAt(position)
  if (!point) return
  if (drawPoints.value.some(p => Math.abs(p[0] - point[0]) < 1e-8 && Math.abs(p[1] - point[1]) < 1e-8)) { mapNotice.value = '这个顶点已添加，请选择其他位置。'; return }
  drawPoints.value.push(point); mapNotice.value = ''; refreshDrawVertices()
}
function undoDraw() { drawPoints.value.pop(); mapNotice.value = ''; refreshDrawVertices() }
function cancelDraw() {
  drawing.value = false; drawCursor.value = null; drawPoints.value = selectedArea.value?.coordinates.slice(0, -1) ?? []; cameraDrawing(false); refreshDrawVertices(); mapNotice.value = ''
}
function clearArea() {
  ++areaRequest; areaAbort?.abort(); areaLoading.value = false; drawing.value = false; selectedArea.value = null; drawPoints.value = []; drawCursor.value = null; cameraDrawing(false)
  if (viewer) { if (areaOutline) viewer.entities.remove(areaOutline); if (areaFill) viewer.entities.remove(areaFill); for (const entity of drawVertices) viewer.entities.remove(entity) }
  areaOutline = null; areaFill = null; drawVertices = []
}
async function finishDraw() {
  if (!drawing.value || areaLoading.value) return
  let coordinates: Coordinate[]
  try { coordinates = closePolygon(drawPoints.value) } catch (error) { mapNotice.value = error instanceof Error ? error.message : '区域无效。'; return }
  selectedArea.value = { coordinates }; drawing.value = false; drawCursor.value = null; cameraDrawing(false); refreshDrawVertices()
  const request = ++areaRequest; areaLoading.value = true; areaAbort = new AbortController(); mapNotice.value = '正在统计圈选区域…'
  try {
    const response = await fetch('/api/map/area-analysis', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ area: selectedArea.value, year: selectedYear.value, quarter: selectedQuarter.value }), signal: areaAbort.signal })
    if (!response.ok) throw new Error('圈选分析失败，请检查区域或重试。')
    const report = readInspectionReport(await response.json())
    if (!report) throw new Error('区域结果格式不完整。')
    if (request !== areaRequest || abort.signal.aborted) return
    applyInspection(report); mapNotice.value = `圈选范围 ${report.summary.checked_count} 家，已超指标 ${report.summary.over_budget} 家，预计超指标 ${report.summary.forecast_risk ?? 0} 家`
    if (!chatRef.value?.isBusy) askArea()
  } catch (error) { if (request === areaRequest && !areaAbort.signal.aborted) mapNotice.value = error instanceof Error ? error.message : '圈选分析失败。' }
  finally { if (request === areaRequest) areaLoading.value = false }
}
function preventContextMenu(event: Event) { event.preventDefault() }
function drawKeydown(event: KeyboardEvent) { if (drawing.value && event.key === 'Escape') { event.preventDefault(); cancelDraw() } }
watch(riversVisible, visible => { if (riverSource) riverSource.show = visible })
watch(() => route.query, () => { routePeriod(); refreshInventory() })
watch(unitsVisible, visible => { hoveredUnit.value = null; for (const entity of entitiesByName.values()) entity.show = visible })
watch(panelOpen, async () => {
  await nextTick()
  if (viewer && !viewer.isDestroyed()) {
    viewer.resize()
    zoomToUnits(visibleUnits.value, inspection.value?.map_view === 'priority')
  }
})
onBeforeUnmount(() => {
  abort.abort()
  areaAbort?.abort()
  canvas?.removeEventListener('contextmenu', preventContextMenu)
  canvas?.removeEventListener('mouseleave', clearHover)
  document.removeEventListener('keydown', drawKeydown)
  removeCameraListener?.()
  clickHandler?.destroy()
  if (viewer && !viewer.isDestroyed()) viewer.destroy()
  viewer = null
})
</script>

<template>
  <div class="map-page" :class="{ 'has-chat': panelOpen }">
    <section class="map-stage" aria-label="用水单位地图">
      <div ref="containerRef" class="map-container"></div>
      <div class="map-search" v-if="!drawing">
        <div class="search-input"><el-icon><Search /></el-icon><input v-model="searchQuery" :disabled="inventoryLoading || areaLoading" placeholder="搜索单位、区县或行业" aria-label="搜索地图单位" @keydown.enter.prevent="searchResults[0] && chooseSearch(searchResults[0])" @keydown.esc="searchQuery = ''"><button v-if="searchQuery" class="icon-button" type="button" aria-label="清空搜索" @click="searchQuery = ''"><el-icon><Close /></el-icon></button></div>
        <div v-if="searchQuery.trim()" class="search-results">
          <button v-for="unit in searchResults" :key="unit.name" type="button" @click="chooseSearch(unit)"><span class="status-dot" :style="{ background: budgetStyles[unit.budget_status].color }"></span><span><strong>{{ unit.name.replace(/（演示）$/, '') }}</strong><small>{{ unit.district }} · {{ unit.industry }}</small></span><b :style="{ color: budgetStyles[unit.budget_status].color }">{{ formatRate(unit) }}</b></button>
          <p v-if="!searchResults.length">当前查询范围内没有匹配单位</p>
        </div>
      </div>

      <div class="map-information">
        <section class="overview-card" aria-label="用水执行概览">
          <div class="overview-heading"><span class="card-mark"><el-icon><Location /></el-icon></span><div><strong>{{ inspection?.area ? '圈选区域分析' : mapMode === 'inspection' ? '用水巡查结果' : '用水执行概览' }}</strong><p class="scope-caption" :title="scopeTitle">{{ scopeTitle }}</p></div><button class="icon-button fold-button" type="button" :aria-expanded="overviewExpanded" aria-controls="map-overview-body" :aria-label="overviewExpanded ? '收起概览' : '展开概览'" @click="overviewExpanded = !overviewExpanded"><el-icon :class="{ folded: !overviewExpanded }"><ArrowDown /></el-icon></button></div>
          <div v-if="!overviewExpanded" class="summary-strip"><span><b>{{ inspection?.summary.checked_count ?? sourceUnits.length }}</b> 家单位</span><span class="mini-count" :style="{ color: budgetStyles.over_budget.color }">已超 {{ currentCounts.over_budget }}</span><span class="mini-count" :style="{ color: budgetStyles.near_limit.color }">预计超 {{ currentCounts.near_limit }}</span></div>
          <div v-show="overviewExpanded" id="map-overview-body">
            <div class="period-controls"><span>{{ selectedYear }} 年</span><select v-model.number="selectedQuarter" :disabled="inventoryLoading || drawing || areaLoading || chatRef?.isBusy" aria-label="统计累计期间" @change="refreshInventory"><option v-for="q in 4" :key="q" :value="q">截至第 {{ q }} 季度末</option></select><span v-if="(inspection ?? inventory)?.demo_mode" class="demo-caption">演示</span></div>
            <p v-if="inventoryLoading" class="data-message">正在加载单位数据…</p><p v-if="inventoryError" class="data-error" role="alert">{{ inventoryError }}</p>
            <template v-if="inventory || inspection || mapMode === 'nearby'">
              <div class="unit-total"><b>{{ inspection?.summary.checked_count ?? sourceUnits.length }}</b><span>{{ inspection ? '家已巡查单位' : '家范围内单位' }}</span><button class="icon-button" type="button" :disabled="inventoryLoading || drawing || areaLoading" title="刷新全部数据" aria-label="刷新全部数据" @click="refreshInventory"><el-icon :class="{ spinning: inventoryLoading }"><RefreshRight /></el-icon></button></div>
              <div class="status-grid"><button v-for="status in statusList" :key="status" type="button" :class="{ selected: unitFilter === status }" :aria-pressed="unitFilter === status" :style="{ '--status-color': budgetStyles[status].color, '--status-tint': budgetStyles[status].color + '0d' }" :disabled="drawing || areaLoading || inventoryLoading" @click="selectStatus(status)"><span><i class="status-dot" :style="{ background: budgetStyles[status].color }"></i>{{ budgetStyles[status].label }}</span><b>{{ currentCounts[status] }}</b></button></div>
              <div class="legend-hint"><span>点击状态筛选地图单位</span><button v-if="unitFilter !== 'all'" type="button" @click="unitFilter = 'all'; renderFiltered()">显示全部</button></div>
            </template>
            <details class="basis-details"><summary>统计与判定口径</summary><p>累计用水 / 有效年度指标 · 单位 m³<br>已超指标：年度执行 &gt;100%<br>预计超指标：按季节进度预测全年超用<br>监督检查建议：已发生超用 &gt;20%（北京案例）</p><p v-if="(inspection ?? inventory)?.demo_mode">单位档案、位置与数值为人工演示样例。</p></details>
            <div v-if="inspection?.area" class="area-totals"><span>核验通过用水 <b>{{ formatAmount(inspection.summary.total_water_used ?? null) }} m³</b></span><span>对应年度指标 <b>{{ formatAmount(inspection.summary.total_budget ?? null) }} m³</b></span><small v-if="inspection.summary.totals_complete === false">合计未纳入待核实单位。</small></div>
            <button class="inspect-button" type="button" :disabled="chatRef?.isBusy || inventoryLoading || drawing || areaLoading" @click="startInspection"><span>{{ chatRef?.isBusy ? '智能体正在处理…' : '一键用水巡查' }}</span><el-icon><ArrowRight /></el-icon></button>
            <div class="map-secondary"><button type="button" :disabled="chatRef?.isBusy || inventoryLoading || drawing || areaLoading" @click="requestReport"><el-icon><Document /></el-icon>生成简报</button><RouterLink :to="{path:'/regulation',query:{year:selectedYear,quarter:selectedQuarter}}">监管工作台 <span>↗</span></RouterLink></div>
            <div v-if="priorityUnits.length" class="priority-list"><div><span>重点核查</span><small>监督检查对象优先</small></div><button v-for="(unit, index) in priorityUnits" :key="unit.name" type="button" @click="selectUnit(unit, true)"><i>{{ index + 1 }}</i><span>{{ unit.name.replace(/（演示）$/, '') }}</span><b :style="{ color: budgetStyles[unit.budget_status].color }">{{ formatRate(unit) }}</b></button></div>
          </div>
        </section>
        <section v-if="selectedUnit && !drawing" class="unit-card" aria-label="用水单位详情">
          <div class="unit-heading"><span class="selected-label">选中单位</span><div><button class="icon-button" type="button" title="定位此单位" aria-label="定位此单位" @click="selectUnit(selectedUnit, true)"><el-icon><Aim /></el-icon></button><button class="icon-button" type="button" aria-label="关闭单位详情" @click="closeSelected"><el-icon><Close /></el-icon></button></div></div>
          <h3>{{ selectedUnit.name.replace(/（演示）$/, '') }}</h3><p class="scope-caption">{{ selectedUnit.district }} · {{ selectedUnit.street }} · {{ selectedUnit.industry }}</p>
          <div class="unit-status" :style="{ color: budgetStyles[selectedUnit.budget_status].color }"><span class="status-dot" :style="{ background: budgetStyles[selectedUnit.budget_status].color }"></span>{{ selectedUnit.status_label }}<b>{{ formatRate(selectedUnit) }}</b></div>
          <div v-if="selectedUnit.execution_rate !== null" class="execution-track"><span :style="{ width: Math.min(100, Math.max(0, selectedUnit.execution_rate)) + '%', background: budgetStyles[selectedUnit.budget_status].color }"></span></div>
          <div class="unit-values"><div><span>本年累计用水</span><b>{{ formatAmount(selectedUnit.water_used) }}<small> m³</small></b></div><div><span>有效年度指标</span><b>{{ formatAmount(selectedUnit.budget) }}<small> m³</small></b></div><div v-if="selectedUnit.forecast_annual != null"><span>预计全年</span><b>{{ formatAmount(selectedUnit.forecast_annual) }}<small> m³</small></b></div><div v-if="selectedUnit.budget_status === 'over_budget'"><span>已发生超用</span><b class="over-value">{{ formatAmount(selectedUnit.over_budget_amount) }}<small> m³</small></b></div></div>
          <p class="period-note">{{ selectedYear }} 年 · 截至第 {{ selectedQuarter }} 季度末</p>
          <p v-if="selectedUnit.inspection_required" class="inspection-alert">超年度指标20%以上，建议监督检查。</p><p v-for="line in selectedUnit.data_issues" :key="line" class="data-message">{{ line }}</p>
          <div class="unit-actions"><button type="button" :disabled="chatRef?.isBusy" @click="askSelected"><el-icon><ChatDotRound /></el-icon>AI 分析</button><RouterLink :to="{path:'/regulation',query:{unit:selectedUnit.name,year:selectedYear,quarter:selectedQuarter,tab:'cases'}}">档案与核查 ↗</RouterLink></div>
        </section>
        <p v-if="riverError" class="map-warning">{{ riverError }}</p>
      </div>

      <nav class="map-tools" aria-label="地图工具">
        <button type="button" title="放大" aria-label="放大地图" @click="cameraZoom('in')"><el-icon><Plus /></el-icon></button><button type="button" title="缩小" aria-label="缩小地图" @click="cameraZoom('out')"><el-icon><Minus /></el-icon></button><span></span>
        <button type="button" :disabled="drawing || areaLoading" :title="selectedUnit ? '定位选中单位' : '适配当前范围'" aria-label="适配地图范围" @click="selectedUnit ? selectUnit(selectedUnit, true) : zoomToUnits(visibleUnits)"><el-icon><Aim /></el-icon></button>
        <button type="button" :disabled="drawing || areaLoading" title="返回全库总览" aria-label="返回全库总览" @click="showInventory(true)"><el-icon><RefreshRight /></el-icon></button><span></span>
        <button type="button" :class="{ active: panelOpen }" :aria-pressed="panelOpen" :title="panelOpen ? '收起AI助手' : '展开AI助手'" :aria-label="panelOpen ? '收起AI助手' : '展开AI助手'" @click="panelOpen = !panelOpen"><el-icon><ChatDotRound /></el-icon></button>
      </nav>
      <div class="map-layerbar" aria-label="图层与圈选"><button type="button" :aria-pressed="riversVisible" :class="{ active: riversVisible }" @click="riversVisible = !riversVisible"><el-icon><Connection /></el-icon>河道</button><button type="button" :aria-pressed="unitsVisible" :class="{ active: unitsVisible }" @click="unitsVisible = !unitsVisible"><el-icon><Location /></el-icon>单位</button><span></span><button type="button" :class="{ active: drawing || selectedArea }" :disabled="drawing || areaLoading || chatRef?.isBusy" @click="startDraw"><el-icon><EditPen /></el-icon>{{ drawing ? '圈选中' : '圈选分析' }}</button><button v-if="selectedArea && !drawing" type="button" title="清除圈选" aria-label="清除圈选区域" @click="showInventory()"><el-icon><Close /></el-icon></button></div>
      <div v-if="drawing" class="draw-guide"><span class="draw-mark"><el-icon><EditPen /></el-icon></span><div><strong>单击地图添加顶点</strong><p>已添加 {{ drawPoints.length }} 个 · 至少3个 · 右键完成 / Esc取消</p></div><button type="button" :disabled="drawPoints.length < 3" @click="finishDraw">完成圈选</button><button type="button" :disabled="!drawPoints.length" @click="undoDraw">撤销</button><button type="button" @click="cancelDraw">取消</button></div>
      <div v-else class="map-status" role="status"><span class="live-dot"></span><span>{{ mapNotice || (unitsVisible ? filterNames[unitFilter] + ' · 显示 ' + visibleUnits.length + ' 家' : '用水单位图层已隐藏') }}</span><button v-if="selectedArea" type="button" :disabled="chatRef?.isBusy || areaLoading" @click="askArea">AI分析区域 ↗</button></div>
      <div v-if="hoveredUnit && !drawing" class="point-tooltip" :style="hoverPosition" aria-hidden="true"><strong>{{ hoveredUnit.name.replace(/（演示）$/, '') }}</strong><div><span class="status-dot" :style="{background:budgetStyles[hoveredUnit.budget_status].color}"></span><span>{{ hoveredUnit.status_label }}</span><b>{{ formatRate(hoveredUnit) }}</b></div><small>{{ hoveredUnit.district }} · 点击查看详情</small></div>
    </section>
    <aside v-show="panelOpen" class="chat-dock" aria-label="水利智能助手"><div class="chat-card"><ChatPanel ref="chatRef" map-linked :map-context="mapContext" @tool-result="onToolResult" @conversation-reset="showInventory(true)" @context-clear="clearContext" /></div></aside>
  </div>
</template>

<style scoped>
.map-page { position:absolute; inset:0; display:grid; grid-template-columns:minmax(0,1fr); background:#f1f4f8; color:#344054; font-family:"Microsoft YaHei",sans-serif; }
.map-page.has-chat { grid-template-columns:minmax(0,1fr) 420px; }
.map-stage { position:relative; min-width:0; min-height:0; overflow:hidden; background:#edf2f6; }
.map-container { position:absolute; inset:0; }
button,input,select { font:inherit; } button { cursor:pointer; } button:disabled { cursor:default; opacity:.45; }
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible { outline:2px solid #6c83ff; outline-offset:3px; }
button,a { -webkit-tap-highlight-color:transparent; } a { text-decoration:none; }
.map-information { position:absolute; top:18px; left:18px; z-index:10; width:264px; max-height:calc(100% - 108px); overflow:auto; scrollbar-width:thin; scrollbar-color:#d7dfed transparent; display:flex; flex-direction:column; gap:12px; padding:1px 4px 8px 1px; }
.overview-card,.unit-card { padding:15px; border-radius:16px; background:rgba(255,255,255,.98); border:1px solid rgba(222,230,241,.85); box-shadow:0 5px 24px rgba(32,53,83,.08),0 1px 4px rgba(32,53,83,.03); }
.overview-heading { display:flex; align-items:center; gap:9px; }
.overview-heading>div { min-width:0; flex:1; }
.overview-heading strong { color:#263b58; font-size:14px; font-weight:600; }
.card-mark { display:grid; place-items:center; width:32px; height:36px; border-radius:10px; color:#647fff; background:#edf2ff; font-size:17px; flex-shrink:0; }
.scope-caption { color:#8b98ac; font-size:10px; line-height:1.7; margin:4px 0 0; }
.overview-heading .scope-caption { white-space:nowrap; text-overflow:ellipsis; overflow:hidden; }
.icon-button { display:grid; place-items:center; width:27px; height:27px; border:0; border-radius:7px; background:transparent; color:#9aa6b8; font-size:14px; flex-shrink:0; }
.icon-button:hover { background:#f2f5fa; color:#586b8b; }
.fold-button { align-self:flex-start; } .fold-button .el-icon { transition:transform .15s; } .fold-button .folded { transform:rotate(180deg); }
.period-controls { display:flex; align-items:center; gap:7px; background:#f7f9fc; border-radius:8px; padding:6px 9px; margin:11px 0 0; color:#7988a0; font-size:10px; }
.period-controls select { min-width:0; flex:1; border:0; padding:0; background:transparent; color:#5e7091; font-size:10px; cursor:pointer; }
.demo-caption { color:#8092c3; font-size:9px; border:1px solid #e2e9f8; border-radius:4px; padding:2px 4px; line-height:1.2; }
.unit-total { display:flex; align-items:baseline; gap:8px; margin:12px 0 10px; } .unit-total>b { font-size:30px; line-height:1; letter-spacing:-1px; color:#263b58; font-weight:600; } .unit-total>span { font-size:10px; color:#8b98ac; } .unit-total .icon-button { margin-left:auto; align-self:center; font-size:13px; }
.status-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.status-grid>button { display:flex; align-items:center; justify-content:space-between; gap:5px; min-width:0; padding:8px; border:1px solid transparent; border-radius:9px; background:var(--status-tint); text-align:left; transition:border-color .15s,background .15s; }
.status-grid>button:hover,.status-grid>button.selected { border-color:var(--status-color); }
.status-grid>button>span { display:flex; align-items:center; gap:5px; color:#76839a; font-size:9px; white-space:nowrap; }
.status-grid b { color:var(--status-color); font-weight:600; font-size:18px; line-height:1.1; font-variant-numeric:tabular-nums; }
.status-dot { display:inline-block; width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.legend-hint { display:flex; align-items:center; justify-content:space-between; font-size:9px; color:#a0aabd; margin:8px 0 10px; }
.legend-hint button { padding:0; border:0; background:transparent; color:#647fff; font-size:9px; }
.basis-details { margin:0 0 11px; padding-top:8px; border-top:1px solid #f0f3f8; color:#93a0b5; font-size:9px; }
.basis-details summary { cursor:pointer; } .basis-details p { line-height:1.9; margin:9px 0 0; }
.inspect-button { display:flex; width:100%; align-items:center; justify-content:space-between; gap:9px; border:0; border-radius:10px; color:#fff; background:#4f6cf7; box-shadow:0 3px 9px #4f6cf71a; padding:11px 12px; font-size:11px; font-weight:500; }
.inspect-button:hover { background:#435fdf; }
.map-secondary { display:flex; align-items:center; justify-content:space-between; gap:8px; margin:12px 0 0; font-size:10px; }
.map-secondary button { display:flex; align-items:center; gap:5px; border:0; background:none; color:#7c8baa; padding:0; font-size:10px; } .map-secondary a { color:#7c8baa; }
.map-secondary a:hover,.map-secondary button:hover { color:#4d6bfe; }
.summary-strip { display:flex; align-items:center; gap:11px; border-top:1px solid #f1f4f8; padding-top:12px; margin-top:12px; font-size:10px; color:#8b98ac; white-space:nowrap; } .summary-strip b { color:#344966; font-size:15px; font-weight:600; } .mini-count { font-size:9px; }
.priority-list { border-top:1px solid #edf1f7; margin-top:14px; padding-top:12px; }
.priority-list>div { display:flex; justify-content:space-between; font-size:10px; color:#8190a8; } .priority-list small { color:#abb4c3; font-size:9px; }
.priority-list button { display:flex; align-items:center; gap:7px; width:100%; background:transparent; border:0; padding:10px 0 0; color:#667995; font-size:10px; text-align:left; }
.priority-list button>i { display:grid; place-items:center; width:17px; height:17px; border-radius:5px; font-size:9px; background:#f2f5fb; color:#95a3b8; font-style:normal; flex-shrink:0; }
.priority-list button>span { white-space:nowrap; text-overflow:ellipsis; overflow:hidden; flex:1; }
.priority-list button>b { flex-shrink:0; font-weight:500; }
.unit-heading { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.unit-heading>div { display:flex; gap:2px; } .selected-label { font-size:10px; color:#96a3b7; }
.unit-card h3 { font-size:14px; font-weight:600; color:#2c405c; margin:6px 0 0; line-height:1.7; }
.unit-status { display:flex; align-items:center; gap:6px; font-size:10px; margin:13px 0 8px; } .unit-status b { margin-left:auto; font-size:17px; font-weight:600; }
.execution-track { height:4px; overflow:hidden; border-radius:5px; background:#eef2f7; } .execution-track>span { height:100%; display:block; border-radius:5px; }
.unit-values { display:grid; grid-template-columns:1fr 1fr; gap:14px 10px; margin:16px 0 0; } .unit-values>div { min-width:0; } .unit-values span { display:block; color:#9aa7ba; font-size:9px; margin:0 0 6px; } .unit-values b { color:#4a5f7b; font-size:14px; font-weight:500; font-variant-numeric:tabular-nums; } .unit-values small { font-size:9px; font-weight:400; color:#a7b1c1; } .unit-values .over-value { color:#d86a6b; }
.period-note { font-size:9px; color:#a4afbf; margin:12px 0 0; }
.inspection-alert { background:#fff5f4; border-radius:7px; padding:8px; font-size:10px; color:#cb7775; line-height:1.7; margin:12px 0 0; }
.unit-actions { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:15px; }
.unit-actions button,.unit-actions a { display:flex; align-items:center; justify-content:center; gap:5px; padding:9px 4px; border:1px solid #e7edf7; border-radius:8px; background:#fff; color:#8b99af; font-size:10px; }
.unit-actions button { background:#eef2ff; color:#5d77ed; border-color:#eef2ff; }
.data-message,.data-error { font-size:10px; line-height:1.8; margin:10px 0 0; } .data-message { color:#97a4b8; } .data-error { color:#cf7575; }
.map-warning { background:#fff; padding:10px 12px; border-radius:9px; color:#9ba6b7; font-size:10px; margin:0; }
.area-totals { display:flex; flex-direction:column; gap:7px; padding:11px; border-radius:9px; background:#f7f9fd; color:#8b9aaf; font-size:10px; margin-bottom:12px; } .area-totals span { display:flex; justify-content:space-between; gap:8px; } .area-totals b { color:#5d718f; font-weight:500; } .area-totals small { font-size:9px; color:#a5afbf; }
.map-search { position:absolute; top:18px; left:310px; right:74px; max-width:300px; z-index:12; }
.search-input { display:flex; align-items:center; gap:9px; height:40px; padding:0 12px; background:rgba(255,255,255,.97); border:1px solid #e5ebf4; border-radius:11px; box-shadow:0 4px 18px #243b5810; }
.search-input>.el-icon { color:#8a9bb3; font-size:15px; }
.search-input input { flex:1; min-width:0; width:100%; padding:0; border:0; outline:0; background:transparent; font-size:11px; color:#536885; height:26px; } .search-input input::placeholder { color:#a4afbf; }
.search-input:focus-within { border-color:#b8c7fa; box-shadow:0 0 0 3px #6c83ff12; }
.search-results { margin-top:7px; padding:5px; border-radius:11px; background:#fff; border:1px solid #e4eaf4; box-shadow:0 10px 30px #243b581a; }
.search-results button { display:flex; align-items:center; gap:8px; width:100%; text-align:left; padding:10px 8px; background:transparent; border:0; border-radius:7px; }
.search-results button:hover { background:#f6f8fc; } .search-results button>span:nth-child(2) { min-width:0; flex:1; } .search-results strong { display:block; font-size:10px; font-weight:500; color:#536885; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; } .search-results small { display:block; color:#a7b1bf; font-size:9px; margin-top:5px; } .search-results b { font-size:10px; font-weight:500; flex-shrink:0; } .search-results p { font-size:10px; color:#98a5b8; margin:10px; line-height:1.8; }
.map-tools { position:absolute; top:18px; right:16px; z-index:11; display:flex; flex-direction:column; padding:5px; border:1px solid #e5ebf4; border-radius:12px; background:rgba(255,255,255,.98); box-shadow:0 4px 18px #243b5810; }
.map-tools>button { display:grid; place-items:center; width:31px; height:32px; border:0; border-radius:7px; background:transparent; color:#7c8fab; font-size:16px; } .map-tools>button:hover,.map-tools>button.active { background:#eff3ff; color:#637ef0; } .map-tools>span { height:1px; background:#edf1f7; margin:4px; }
.map-layerbar { position:absolute; bottom:43px; right:16px; display:flex; align-items:center; gap:4px; padding:5px; border-radius:10px; border:1px solid #e5ebf4; background:rgba(255,255,255,.97); box-shadow:0 4px 18px #243b5810; z-index:11; }
.map-layerbar button { display:flex; align-items:center; justify-content:center; gap:5px; border:0; border-radius:6px; background:transparent; padding:7px 8px; color:#99a5b8; font-size:10px; } .map-layerbar button.active,.map-layerbar button:hover { background:#f0f4ff; color:#6881eb; } .map-layerbar>span { height:16px; width:1px; background:#e9eef6; margin:0 3px; }
.map-status { position:absolute; bottom:14px; right:16px; z-index:10; max-width:calc(100% - 315px); display:flex; align-items:center; gap:7px; color:#8494aa; font-size:9px; padding:6px 9px; background:#fffffff0; border:1px solid #e6ecf4; border-radius:7px; line-height:1.7; }
.live-dot { width:5px; height:5px; border-radius:50%; background:#84a998; flex-shrink:0; } .map-status button { border:0; background:transparent; color:#647fff; font-size:9px; padding:0 3px; white-space:nowrap; }
.map-status>span:nth-child(2) { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.draw-guide { position:absolute; bottom:95px; left:50%; transform:translateX(-50%); z-index:13; display:flex; align-items:center; gap:10px; width:max-content; max-width:calc(100% - 32px); box-sizing:border-box; border-radius:12px; padding:12px 14px; background:#fff; border:1px solid #dce5f6; box-shadow:0 6px 24px #344e701f; }
.draw-mark { display:grid; place-items:center; width:32px; height:32px; border-radius:8px; color:#6881eb; background:#f0f4ff; } .draw-guide strong { font-size:11px; font-weight:500; color:#526887; } .draw-guide p { font-size:9px; color:#9ba9bd; margin:5px 0 0; line-height:1.7; } .draw-guide button { border:1px solid #e3eaf7; border-radius:7px; padding:7px 9px; background:#fff; color:#8293ae; font-size:10px; white-space:nowrap; } .draw-guide button:first-of-type { color:#fff; background:#617df0; border-color:#617df0; }
.point-tooltip { position:absolute; z-index:14; width:220px; box-sizing:border-box; padding:12px 14px; background:#fff; border:1px solid #dfe7f4; border-radius:12px; box-shadow:0 8px 26px #22395822; pointer-events:none; }
.point-tooltip strong { display:block; font-size:11px; color:#425978; font-weight:500; } .point-tooltip>div { display:flex; align-items:center; gap:6px; font-size:10px; color:#8e9cb1; margin-top:9px; } .point-tooltip b { margin-left:auto; color:#526887; font-weight:500; } .point-tooltip small { display:block; font-size:9px; color:#a4afbf; margin-top:8px; }
.chat-dock { min-width:0; min-height:0; padding:14px 14px 14px 0; box-sizing:border-box; position:relative; z-index:15; }
.chat-card { height:100%; background:#fff; border:1px solid #e4eaf3; border-radius:16px; box-shadow:0 5px 24px #2035530a; overflow:hidden; }
.chat-card :deep(.panel-head) { padding:16px 18px; } .chat-card :deep(.welcome) { padding:25px 0 12px; } .chat-card :deep(.welcome h2) { font-size:20px; } .chat-card :deep(.welcome p) { font-size:12px; margin-bottom:22px; } .chat-card :deep(.suggestions button) { font-size:12px; padding:11px 12px; }
.spinning { animation:spin 1s linear infinite; } @keyframes spin { to { transform:rotate(360deg); } }
@media(max-width:1280px) { .map-page.has-chat {grid-template-columns:minmax(0,1fr) 380px;} .map-information {width:244px;left:14px;top:14px;} .overview-card,.unit-card {padding:15px;} .map-search {left:282px;top:14px;} .map-tools {top:14px;right:14px;} .chat-dock {padding:12px 12px 12px 0;} }
@media(max-width:1100px) { .map-search {display:none;} .map-page.has-chat {grid-template-columns:minmax(0,1fr) 360px;} .map-information {width:228px;} .map-layerbar {right:12px;} .draw-guide {gap:6px;flex-wrap:wrap;justify-content:center;} }
@media(max-width:800px) { .map-page.has-chat {grid-template-columns:minmax(0,1fr);} .map-page.has-chat .map-information,.map-page.has-chat .map-layerbar,.map-page.has-chat .map-status {display:none;} .chat-dock {position:absolute;right:12px;left:66px;top:0;bottom:0;padding:12px 0;max-width:400px;margin-left:auto;} .map-tools {right:auto;left:12px;z-index:20;} .map-information {left:66px;width:min(244px,calc(100% - 86px));} .map-status {max-width:calc(100% - 90px);} .point-tooltip {display:none;} }
@media(prefers-reduced-motion:reduce) { .fold-button .el-icon {transition:none;} .spinning {animation:none;} }
</style>
