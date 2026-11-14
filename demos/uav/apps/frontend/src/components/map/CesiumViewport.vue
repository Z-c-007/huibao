<template>
  <div class="map-shell">
    <div ref="mapRef" class="map-shell__canvas"></div>

    <!-- <div class="map-shell__overlay map-shell__overlay--top">
      <StatusBadge :label="mapReady ? 'scene ready' : 'scene loading'" :tone="mapReady ? 'success' : 'warning'" />
      <StatusBadge :label="sceneLabel" tone="info" />
    </div> -->

    <div class="map-shell__overlay map-shell__overlay--bottom">
      <div class="map-shell__status-card">
        <span>地图状态</span>
        <strong>{{ mapStatus }}</strong>
        <el-button
          @click="addElectronicFence"
          style="position: absolute; bottom: 60px; right: 16px; z-index: 100000"
        >
          添加电子围栏
        </el-button>

        <el-button
          @click="setFlightPath"
          :disabled="isSettingPath"
          style="position: absolute; bottom: 90px; right: 16px; z-index: 100000"
        >
          设置航线
        </el-button>
        <el-button
          @click="pathPlanning"
          :disabled="!draftWaypoints.length || isPlanning"
          :loading="isPlanning"
          style="
            position: absolute;
            bottom: 120px;
            right: 16px;
            z-index: 100000;
          "
        >
          路径规划
        </el-button>
        <el-button
          @click="DroneFlyToPosition"
          style="
            position: absolute;
            bottom: 150px;
            right: 16px;
            z-index: 100000;
          "
        >
          开始飞行
        </el-button>
        <el-button
          @click="resetScene"
          style="
            position: absolute;
            bottom: 180px;
            right: 16px;
            z-index: 100000;
          "
        >
          重置场景
        </el-button>
        <el-button
          @click="pathPlanningByWS"
          :loading="isWSPlanning"
          style="
            position: absolute;
            bottom: 210px;
            right: 16px;
            z-index: 100000;
          "
        >
          路径规划ws
        </el-button>
      </div>
      <EntityConfiguration />
      <!-- 实体配置组件 -->
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import StatusBadge from "@/components/common/StatusBadge.vue";
import { flyToBoundingSphere } from "@/services/cesium/camera";
import { addTileset } from "@/services/cesium/entities";
import { DroneFlightController } from "@/services/cesium/move/DroneFlightController";
import { useFenceManager } from "../../hooks/useFenceManager";
import { useCesium } from "@/hooks/useCesium";
import { GeofencePicker } from "@/utils/PickPosition/ElectronicFencePicker";
import { ElButton, ElMessage } from "element-plus";
import {
  cartesian3ToLngLats,
  lngLatsToCartesian3,
} from "@/utils/DrawObstacle/utils";
import EntityConfiguration from "../common/EntityConfiguration.vue";
import { useEntityDataStore } from "@/stores/EntityData";
import { useRouteFlyDataStore } from "@/stores/routeFlyData";
import type { RouteFlyWaypoint } from "@/stores/routeFlyData";
import { generateUniqueID } from "@uav/shared";
import { RoutePlanPicker } from "@/utils/PickPosition/routePlanPicker";
import type { AStarWaypoint } from "@/utils/AStar3DPathPlanner";
import { usePathPlanner } from "@/hooks/usePathPlanner";
import { useDroneSocket } from "@/hooks/useDroneSocket";
import { RoutePlan } from "../../utils/RoutePlan/routePlan";
const { viewer, status, initMap, getTerrainManager } = useCesium();
const mapRef = ref<HTMLDivElement | null>(null);
const mapStatus = status;
const mapReady = ref(false);
const sceneLabel = ref("Mock City");
const cesiumToken = import.meta.env.VITE_CESIUM_TOKEN?.trim();
let persistentRoutePlan: RoutePlan | null = null; // 持久化路线可视化
const draftWaypoints: AStarWaypoint[] = []; // 原始航点（供规划用）
const isSettingPath = ref(false); // 是否正在绘制
let fencePicker: GeofencePicker | null = null; // 电子围栏拾取器实例
let routePlanPicker: RoutePlanPicker | null = null; // 路径规划拾取器实例

let flightController: DroneFlightController | null = null;
const entityDataStore = useEntityDataStore();
const routeFlyDataStore = useRouteFlyDataStore();

const { avoidObstacles, isPlanning } = usePathPlanner();
const {
  isConnected: isWSConnected,
  connect: connectWS,
  planRoute: planRouteWS,
} = useDroneSocket();
const isWSPlanning = ref(false);
/**
 * 测试前后端飞行(ws)
 */
const pathPlanningByWS = async () => {
  if (!draftWaypoints.length) {
    ElMessage.warning("请先设置路径");
    return;
  }
  if (!isWSConnected.value) {
    ElMessage.warning("WebSocket 未连接，正在尝试连接...");
    connectWS();
    return; // 或者等待连接后再继续
  }
  isWSPlanning.value = true;
  mapStatus.value = "WS路径规划中...";
  try {
    const waypoints = await planRouteWS(draftWaypoints);
    routeFlyDataStore.addRoute({
      id: generateUniqueID(),
      name: `WS路线 ${routeFlyDataStore.routeCount + 1}`,
      waypoints,
      createdAt: Date.now(),
      color: "#FF6B35", // 橙色，区分于本地算法的蓝色
    });
    mapStatus.value = "WS路径规划完成";
    ElMessage.success("后端路径规划完成");
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "规划失败";
    mapStatus.value = message;
    ElMessage.error(message);
  } finally {
    isWSPlanning.value = false;
  }
};
/**
 * 开始飞行
 */
const DroneFlyToPosition = async () => {
  const v = viewer.value;
  if (!v) return;
  const waypoints = routeFlyDataStore.activeWaypoints;
  if (!waypoints.length) {
    ElMessage.warning("请先选择一条路线");
    return;
  }

  flightController?.destroy();

  flightController = new DroneFlightController(v, {
    modelUrl: "/models/uav.glb",
    scale: 3,
    minimumPixelSize: 128,
    cruiseSpeed: 80,
    speed: 0.2,
    showPath: true,
    heightOffset: 1,
  });

  flightController.fly(waypoints, {
    onStart: () => {
      mapStatus.value = "飞行中";
    },
    onWaypointReach: (wp, i) => {
      // console.log(`到达航点 ${i + 1}:`, wp);
    },
    onComplete: () => {
      mapStatus.value = "飞行完成";
      ElMessage.success("飞行完成");
      flightController?.destroy();
    },
  });

  mapReady.value = true;
  mapStatus.value = "加载模型可用";
};
/**
 * 添加电子围栏
 */
const addElectronicFence = async () => {
  const v = viewer.value;
  if (!v) return;
  fencePicker = new GeofencePicker({ viewer: v });

  const points = await fencePicker.startAsync();
  const lngLats = cartesian3ToLngLats(points);
  entityDataStore.addElectronicFence({
    id: generateUniqueID(),
    coordinates: lngLats,
    fillColor: Cesium.Color.RED.withAlpha(0.5).toCssColorString(),
    height: 10,
  });
  ElMessage.success("电子围栏添加成功");
};
/**
 * 设置航线
 */
const setFlightPath = async () => {
  const v = viewer.value;
  if (!v) return;

  // 销毁旧路线
  persistentRoutePlan?.destroy();
  persistentRoutePlan = null;
  draftWaypoints.length = 0;

  // 清理旧拾取器
  routePlanPicker?.cancel();
  routePlanPicker?.clear();
  routePlanPicker = new RoutePlanPicker({ viewer: v });

  isSettingPath.value = true;

  // 用户点选航点（右键完成）
  await routePlanPicker.startAsync();
  isSettingPath.value = false;

  // 保存路线可视化和原始航点
  persistentRoutePlan = routePlanPicker.getRoutePlan();
  const positions = routePlanPicker.getPositions();
  draftWaypoints.splice(
    0,
    draftWaypoints.length,
    ...cartesian3ToLngLats(positions).map(([lng, lat, altitude]) => ({
      lat,
      lng,
      altitude,
    })),
  );

  routePlanPicker = null; // picker 使命完成
  ElMessage.success("路径已设置，可点击'路径规划'进行避障分析");
};
/**
 * 路径规划
 */
const pathPlanning = async () => {
  if (!draftWaypoints.length) {
    ElMessage.warning("请先设置路径");
    return;
  }

  // 3. 从 Store 准备禁飞区数据
  const zones = entityDataStore.electronicFences.map((fence) => ({
    minLat: Math.min(...fence.coordinates.map(([, lat]) => lat)),
    maxLat: Math.max(...fence.coordinates.map(([, lat]) => lat)),
    minLng: Math.min(...fence.coordinates.map(([lng]) => lng)),
    maxLng: Math.max(...fence.coordinates.map(([lng]) => lng)),
    minAlt: 0,
    maxAlt: fence.height ?? 100,
  }));
  console.log("从store里面读禁飞区的值", zones);

  // 4. 🔥 Worker 异步避障 — 不阻塞主线程
  mapStatus.value = "路径规划中..."; // UI 实时反馈

  try {
    const safePath = await avoidObstacles(draftWaypoints, zones);
    console.log("避障后的安全路径", safePath);
    if (!safePath) {
      ElMessage.error("当前路径经过禁飞区，无法生成安全航线，请重新设置路径");
      mapStatus.value = "路径规划失败 — 航线经过禁飞区";
      return;
    }
    // 5. 处理结果
    const waypoints: RouteFlyWaypoint[] = safePath.map((p, i) => ({
      ...p,
      order: i + 1,
    }));

    routeFlyDataStore.addRoute({
      id: generateUniqueID(),
      name: `路线 ${routeFlyDataStore.routeCount + 1}`,
      waypoints,
      createdAt: Date.now(),
      color: "#00BFFF",
    });

    mapStatus.value = "路径规划完成";
    ElMessage.success("路径规划完成");
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "路径规划失败";
    mapStatus.value = message;
    ElMessage.error(message);
    // 失败时清理本次绘制的实体
    routePlanPicker?.clear();
    routePlanPicker = null;
  }
};

async function loadScene() {
  if (!mapRef.value) {
    return;
  }

  mapStatus.value = "正在创建 Cesium Viewer";

  await initMap(mapRef.value!, {
    accessToken: cesiumToken,
  });
  const v = viewer.value;
  if (!v) return;
  // viewer.extend(Cesium.viewerCesiumInspectorMixin); // 开发阶段启用 Cesium Inspector 插件，方便调试场景性能和效果
  useFenceManager(v); // 初始化围栏管理逻辑

  if (cesiumToken) {
    try {
      mapStatus.value = "正在加载城市模型";
      const tileset = await addTileset(v, {
        assetId: 75343,
      });
      sceneLabel.value = "Ion 3D Tiles";
      mapStatus.value = "城市模型加载完成";
      flyToBoundingSphere(v, tileset.boundingSphere, {
        duration: 2,
        heading: 30,
        pitch: -60,
        range: tileset.boundingSphere.radius * 0.8,
      });
    } catch (error) {
      console.error("Failed to load tileset:", error);
      mapStatus.value = "城市模型加载失败，已切换到演示场景";
      sceneLabel.value = "Fallback Scene";
    }
  } else {
    mapStatus.value = "未配置 Ion Token，使用演示场景";
    sceneLabel.value = "Local Demo Scene";
  }
}
const resetScene = () => {
  const v = viewer.value;
  if (!v) return;
  console.log("重置场景");

  entityDataStore.clearElectronicFences();
  routeFlyDataStore.clearAllRoutes();
  flightController?.destroy();
  persistentRoutePlan?.destroy(); // ← 新增
  persistentRoutePlan = null; // ← 新增
  draftWaypoints.length = 0; // ← 新增
  isSettingPath.value = false;
};
onMounted(async () => {
  await loadScene();
  connectWS(); // 组件挂载时自动连接 WebSocket
});
onBeforeUnmount(() => {
  fencePicker?.clear();
  routePlanPicker?.clear();
  flightController?.destroy();
  persistentRoutePlan?.destroy();
  persistentRoutePlan = null;
  fencePicker = null;
  routePlanPicker = null;
  flightController = null;
});
</script>

<style scoped>
.map-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-radius: 18px;
}

.map-shell__canvas {
  width: 100%;
  height: 100%;
}

.map-shell__overlay {
  position: absolute;
  left: 16px;
  right: 16px;
  display: flex;
  justify-content: space-between;
  /* pointer-events: none; */
}

.button {
  display: flex;
  align-items: center;
  gap: 10px;
}

.map-shell__overlay--top {
  top: 16px;
  right: auto;
  gap: 10px;
  justify-content: flex-start;
}

.map-shell__overlay--bottom {
  bottom: 16px;
}

.map-shell__status-card {
  max-width: 340px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.76);
  border: 1px solid rgba(148, 163, 184, 0.18);
  backdrop-filter: blur(12px);
}

.map-shell__status-card span {
  display: block;
  font-size: 11px;
  color: #94a3b8;
}

.map-shell__status-card strong {
  display: block;
  margin-top: 6px;
  font-size: 14px;
  color: #f8fafc;
}
</style>
