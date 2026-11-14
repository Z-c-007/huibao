import {
  ref,
  shallowRef,
  triggerRef,
  onBeforeUnmount,
  shallowReadonly,
} from "vue";
import * as Cesium from "cesium";
import { createViewer, destroyViewer } from "@/services/cesium/viewer";
import { createScene } from "@/services/cesium/scene";
import {
  TerrainManager,
  TerrainSourceType,
  DEFAULT_TERRAIN_CONFIG,
} from "../services/cesium/terrain";

import type { TerrainConfig } from "@/services/cesium/terrain";

/**
 * useCesium —— 桥接层 Composable
 *
 * 职责：
 *   1. 管理 Cesium Viewer 的完整生命周期（创建 → 就绪 → 销毁）
 *   2. 编排 TerrainManager 的地形初始化
 *   3. 为 UI 层暴露只读的响应式状态（viewer / isReady / status）
 *
 * 关键约束（SKILL.md）：
 *   - 使用 shallowRef 包装 Viewer，严禁 deep reactive
 *   - 不包含具体 Cesium 原生 API 调用（委托给核心 GIS 层）
 */

/** useCesium 的初始化选项 */
export interface UseCesiumInitOptions {
  /** Cesium Ion Token */
  accessToken?: string;
  /** 地形配置（不传则默认用 ellipsoid 低配模式） */
  terrainConfig?: Partial<TerrainConfig>;
}

// TerrainManager 不需要响应式（纯逻辑层，通过 getter 暴露）
let terrainManager: TerrainManager | null = null;
export function useCesium() {
  const viewer = shallowRef<Cesium.Viewer | null>(null);
  const isReady = ref(false);
  const status = ref("等待初始化");
  /**
   * 初始化 Cesium 地图
   *
   * 调用链：createViewer → createScene → TerrainManager.initialize
   *
   * @param container - HTML 容器元素
   * @param options - 初始化选项
   * @returns 创建好的 Viewer 实例
   */
  async function initMap(
    container: HTMLElement,
    options: UseCesiumInitOptions = {},
  ) {
    // 1. 创建 Viewer（先用低配椭球面，避免空窗期无 terrainProvider）
    status.value = "正在创建 Cesium Viewer";
    const v = createViewer(container, {
      accessToken: options.accessToken,
      viewerOptions: {
        terrainProvider: new Cesium.EllipsoidTerrainProvider(),
      },
    });
    viewer.value = v;

    // 2. 应用场景配置（抗锯齿、光照、深度测试等）
    createScene(v);

    // 3. 初始化地形
    if (options.accessToken) {
      const terrainCfg: Partial<TerrainConfig> = {
        ...DEFAULT_TERRAIN_CONFIG,
        ...options.terrainConfig,
      };

      // 如果外部未显式指定地形类型，默认用 Cesium Ion World Terrain
      if (!options.terrainConfig?.type) {
        terrainCfg.type = TerrainSourceType.CESIUM_ION;
      }

      terrainManager = new TerrainManager(v, terrainCfg);

      try {
        status.value = "正在加载地形数据";
        await terrainManager.initialize();
        status.value = "地形数据加载完成";
      } catch (err) {
        console.warn("[useCesium] 地形加载失败，降级为椭球面:", err);
        status.value = "地形加载失败，使用低配模式";
      }
    }

    isReady.value = true;
    status.value = "场景就绪";
    return v;
  }

  /** 获取 TerrainManager 实例（供外部模块查询地形高度） */
  function getTerrainManager(): TerrainManager | null {
    return terrainManager;
  }

  /**
   * 通知 Vue shallowRef 的值内部已变（用于非替换型更新）
   *
   * 使用场景：当 Cesium 内部状态变化（如 Entity 被添加/移除）但 .value 引用不变时，
   *           调用此方法手动触发依赖此 ref 的组件更新
   */
  function notifyViewerChange(): void {
    triggerRef(viewer);
  }
  /**
   * 清理所有资源
   *
   * 销毁顺序：TerrainManager → Viewer
   * 必须在地形管理器销毁后再销毁 Viewer，避免 Viewer 关闭时地形仍在请求瓦片
   */
  function dispose(): void {
    terrainManager?.destroy();
    terrainManager = null;

    viewer.value = destroyViewer(viewer.value);
    isReady.value = false;
    status.value = "已销毁";
  }
  onBeforeUnmount(() => {
    dispose();
  });

  return {
    /** Viewer 只读引用（shallowRef，响应式但非深度劫持） */
    viewer: shallowReadonly(viewer),
    /** 是否就绪 */
    isReady: isReady,
    /** 当前状态文案 */
    status: status,
    initMap,
    getTerrainManager,
    notifyViewerChange,
    dispose,
  };
}
