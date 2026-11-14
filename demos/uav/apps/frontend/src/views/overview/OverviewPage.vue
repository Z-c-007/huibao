<template>
  <DashboardLayout>
    <template #header>
      <WorkspaceHeader :title="appStore.systemName" :stats="headerStats" />
    </template>

    <template #left>
      <AppPanel title="任务队列">
        <div class="list-stack">
          <button
            v-for="mission in missionStore.missions"
            :key="mission.id"
            class="list-item"
            :class="{
              'list-item--active':
                mission.id === missionStore.selectedMissionId,
            }"
            @click="missionStore.selectMission(mission.id)"
          >
            <div class="list-item__top">
              <strong>{{ mission.name }}</strong>
              <StatusBadge
                :label="mission.priority"
                :tone="priorityToneMap[mission.priority]"
              />
            </div>
            <p>{{ mission.code }} · {{ mission.type }}</p>
            <div class="list-item__meta">
              <span>{{ mission.status }}</span>
              <span>{{ formatDistanceKm(mission.totalDistanceKm) }}</span>
              <span>{{
                formatDurationMinutes(mission.estimatedDurationMinutes)
              }}</span>
            </div>
          </button>
        </div>
      </AppPanel>

      <AppPanel title="空域与障碍">
        <div class="list-stack">
          <button
            v-for="zone in obstacleStore.zones"
            :key="zone.id"
            class="list-item"
            :class="{
              'list-item--active': zone.id === obstacleStore.selectedZoneId,
            }"
            @click="obstacleStore.selectZone(zone.id)"
          >
            <div class="list-item__top">
              <strong>{{ zone.name }}</strong>
              <StatusBadge
                :label="zone.riskLevel"
                :tone="riskToneMap[zone.riskLevel]"
              />
            </div>
            <p>{{ zone.type }} · {{ zone.activeTime }}</p>
            <div class="list-item__meta">
              <span>{{ formatAltitude(zone.minAltitude) }}</span>
              <span>{{ formatAltitude(zone.maxAltitude) }}</span>
            </div>
          </button>
        </div>
      </AppPanel>
    </template>

    <AppPanel title="三维调度总览">
      <template #action>
        <div class="toolbar">
          <button
            v-for="layer in mapStore.layers"
            :key="layer.key"
            class="toolbar__chip"
            :class="{ 'toolbar__chip--active': layer.enabled }"
            @click="mapStore.toggleLayer(layer.key)"
          >
            {{ layer.label }}
          </button>
        </div>
      </template>

      <div class="overview-map">
        <CesiumViewport />
      </div>
    </AppPanel>

    <template #right>
      <AppPanel title="无人机详情">
        <template v-if="selectedDrone">
          <div class="detail-card">
            <div class="detail-card__top">
              <div>
                <h3>{{ selectedDrone.name }}</h3>
                <p>{{ selectedDrone.code }} · {{ selectedDrone.model }}</p>
              </div>
              <StatusBadge
                :label="selectedDrone.status"
                :tone="droneToneMap[selectedDrone.status]"
              />
            </div>

            <dl class="detail-grid">
              <div>
                <dt>电量</dt>
                <dd>{{ formatPercent(selectedDrone.battery) }}</dd>
              </div>
              <div>
                <dt>信号</dt>
                <dd>{{ formatPercent(selectedDrone.signal) }}</dd>
              </div>
              <div>
                <dt>高度</dt>
                <dd>{{ formatAltitude(selectedDrone.location.altitude) }}</dd>
              </div>
              <div>
                <dt>速度</dt>
                <dd>{{ selectedDrone.speed }} m/s</dd>
              </div>
              <div>
                <dt>航向</dt>
                <dd>{{ selectedDrone.heading }}°</dd>
              </div>
              <div>
                <dt>风险</dt>
                <dd>{{ selectedDrone.riskLevel }}</dd>
              </div>
            </dl>

            <p class="detail-card__remark">
              最后上报：{{ selectedDrone.updatedAt }}
            </p>
          </div>
        </template>
      </AppPanel>

      <AppPanel title="告警中心">
        <div class="list-stack">
          <button
            v-for="alert in alertStore.alerts"
            :key="alert.id"
            class="list-item"
            :class="{
              'list-item--active': alert.id === alertStore.highlightedAlertId,
            }"
            @click="handleAlertClick(alert.id)"
          >
            <div class="list-item__top">
              <strong>{{ alert.title }}</strong>
              <StatusBadge
                :label="alert.level"
                :tone="alertToneMap[alert.level]"
              />
            </div>
            <p>{{ alert.content }}</p>
            <div class="list-item__meta">
              <span>{{ alert.time }}</span>
              <span>{{ alert.status }}</span>
            </div>
          </button>
        </div>
      </AppPanel>
    </template>

    <!-- <template #footer>
      <WorkspaceFooter :items="footerMetrics" />
    </template> -->
  </DashboardLayout>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import AppPanel from "@/components/common/AppPanel.vue";
import StatusBadge from "@/components/common/StatusBadge.vue";
// import WorkspaceFooter from "@/components/layout/WorkspaceFooter.vue";
import WorkspaceHeader from "@/components/layout/WorkspaceHeader.vue";
import CesiumViewport from "@/components/map/CesiumViewport.vue";
import DashboardLayout from "@/layouts/DashboardLayout.vue";
import { useAlertStore } from "@/stores/alert";
import { useAppStore } from "@/stores/app";
import { useDroneStore } from "@/stores/drone";
import { useMapStore } from "@/stores/map";
import { useMissionStore } from "@/stores/mission";
import { useObstacleStore } from "@/stores/obstacle";
import {
  formatAltitude,
  formatDistanceKm,
  formatDurationMinutes,
  formatPercent,
} from "@/utils/format";

const appStore = useAppStore();
const mapStore = useMapStore();
const droneStore = useDroneStore();
const missionStore = useMissionStore();
const obstacleStore = useObstacleStore();
const alertStore = useAlertStore();

const { selectedDrone } = storeToRefs(droneStore);

const headerStats = computed(() => [
  {
    label: "在线无人机",
    value: `${droneStore.onlineCount}/${droneStore.drones.length}`,
  },
  { label: "执行中任务", value: `${missionStore.executingCount}` },
  { label: "关键告警", value: `${alertStore.criticalCount}` },
]);

// const footerMetrics = computed(() => [
//   { label: "已启用图层", value: `${mapStore.enabledLayerCount}` },
//   { label: "高风险区域", value: `${obstacleStore.highRiskCount}` },
//   { label: "未读告警", value: `${alertStore.unreadCount}` },
//   { label: "当前模式", value: appStore.mode },
// ]);

const priorityToneMap = {
  P0: "danger",
  P1: "warning",
  P2: "info",
} as const;

const riskToneMap = {
  low: "success",
  medium: "warning",
  high: "danger",
} as const;

const droneToneMap = {
  idle: "neutral",
  ready: "info",
  executing: "success",
  returning: "warning",
  warning: "danger",
  offline: "neutral",
} as const;

const alertToneMap = {
  info: "info",
  warning: "warning",
  critical: "danger",
} as const;

function handleAlertClick(id: string) {
  alertStore.highlightAlert(id);
  alertStore.markAsRead(id);
}
</script>

<style scoped>
.list-stack {
  /* display: flex; */
  /* flex-direction: column; */
  /* gap: 10px; */
  min-height: 0;
  /* overflow: auto; */
}

.list-item {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.38);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    transform 160ms ease,
    background 160ms ease;
}

.list-item:hover,
.list-item--active {
  border-color: rgba(125, 211, 252, 0.32);
  background: rgba(30, 41, 59, 0.76);
  transform: translateY(-1px);
}

.list-item__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.list-item strong {
  color: #f8fafc;
  font-size: 14px;
}

.list-item p {
  margin-top: 8px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.list-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
  font-size: 11px;
  color: #7dd3fc;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar__chip {
  padding: 8px 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 999px;
  background: rgba(30, 41, 59, 0.72);
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
}

.toolbar__chip--active {
  border-color: rgba(125, 211, 252, 0.4);
  color: #e0f2fe;
}

.overview-map {
  flex: 1;
  min-height: 0;
}

.detail-card {
  padding: 16px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.48);
}

.detail-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.detail-card__top h3 {
  font-size: 18px;
  color: #f8fafc;
}

.detail-card__top p {
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
  margin-top: 18px;
}

.detail-grid dt {
  font-size: 11px;
  color: #94a3b8;
}

.detail-grid dd {
  margin-top: 4px;
  font-size: 15px;
  font-weight: 700;
  color: #f8fafc;
}

.detail-card__remark {
  margin-top: 18px;
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 1180px) {
  .overview-map {
    min-height: 360px;
  }
}
</style>
