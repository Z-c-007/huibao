import * as Cesium from "cesium";
import { TerrainSourceType, DEFAULT_TERRAIN_CONFIG } from "./types";
import type { TerrainConfig } from "./types";

/**
 * 地形管理器 —— 核心 GIS 层
 *
 * 职责：
 *   1. 封装地形提供者 (TerrainProvider) 的创建逻辑
 *   2. 支持运行时切换地形源（低配椭球 → Ion在线 → 自建服务）
 *   3. 提供地形高度查询（同步/异步），供避障和 AGL 计算使用
 *   4. 管理地形资源的销毁，防止内存泄漏
 *
 * 完全脱离 Vue，纯 TypeScript 类。
 */
export class TerrainManager {
  private _viewer: Cesium.Viewer;
  private _config: TerrainConfig;
  private _initialized = false;

  constructor(viewer: Cesium.Viewer, config?: Partial<TerrainConfig>) {
    this._viewer = viewer;
    this._config = { ...DEFAULT_TERRAIN_CONFIG, ...config } as TerrainConfig;
  }

  /** 是否已初始化 */
  get initialized(): boolean {
    return this._initialized;
  }

  /** 当前地形配置（只读） */
  get config(): Readonly<TerrainConfig> {
    return this._config;
  }

  /**
   * 初始化地形 —— 根据配置创建 TerrainProvider 并挂载到 Viewer
   *
   * 调用时机：Viewer 创建完成后、加载城市模型之前
   */
  async initialize(): Promise<Cesium.TerrainProvider> {
    if (this._viewer.isDestroyed()) {
      throw new Error("[TerrainManager] Viewer 已销毁，无法初始化地形");
    }

    const provider = await this._createProvider();
    this._viewer.terrainProvider = provider;
    this._initialized = true;
    return provider;
  }

  /**
   * 运行时切换地形数据源
   *
   * 使用场景：
   *   - 用户从低配模式切换到高精度地形
   *   - 无人机进入不同作业区，切换对应级别的 DEM
   */
  async switchTerrainSource(
    type: TerrainSourceType,
    overrides?: Partial<TerrainConfig>,
  ): Promise<Cesium.TerrainProvider> {
    if (this._viewer.isDestroyed()) {
      throw new Error("[TerrainManager] Viewer 已销毁，无法切换地形");
    }

    this._config = { ...this._config, ...overrides, type };
    const provider = await this._createProvider();
    this._viewer.terrainProvider = provider;
    return provider;
  }

  /**
   * 同步获取某点的地形海拔高度（米，相对于 WGS84 椭球面）
   *
   * 注意：如果瓦片未加载完成，返回 undefined
   * 适用于不需要精确高度的场景（粗粒度避障预判）
   *
   * @param lng - 经度
   * @param lat - 纬度
   * @returns 地形海拔（米），瓦片未就绪时返回 undefined
   */
  getHeight(lng: number, lat: number): number | undefined {
    if (this._viewer.isDestroyed()) return undefined;

    // 将经纬度转为弧度制 Cartographic 坐标
    // 注意：这里高度传入 0，因为我们要查询的是该位置的地形表面高度
    const cartographic = Cesium.Cartographic.fromDegrees(lng, lat);
    const height = this._viewer.scene.globe.getHeight(cartographic);

    return height;
  }

  /**
   * 异步获取某点的精确地形海拔（等待瓦片加载完成后返回）
   *
   * 使用 Cesium.sampleTerrainMostDetailed 确保拿到该点最高精度的地形数据
   * 适用于需要精确 AGL 计算的场景（无人机起降、低空飞行）
   *
   * @param lng - 经度
   * @param lat - 纬度
   * @returns 精确地形海拔（米）
   */
  async sampleHeight(lng: number, lat: number): Promise<number> {
    const positions = [Cesium.Cartographic.fromDegrees(lng, lat)];
    const updatedPositions = await Cesium.sampleTerrainMostDetailed(
      this._viewer.terrainProvider,
      positions,
    );
    return updatedPositions[0]?.height ?? 0;
  }

  /**
   * 批量异步查询多点地形海拔（性能优于逐个调用 sampleHeight）
   *
   * @param points - 经纬度数组
   * @returns 对应的海拔数组
   */
  async sampleHeightBatch(
    points: Array<{ lng: number; lat: number }>,
  ): Promise<number[]> {
    const cartographics = points.map((p) =>
      Cesium.Cartographic.fromDegrees(p.lng, p.lat),
    );
    const updated = await Cesium.sampleTerrainMostDetailed(
      this._viewer.terrainProvider,
      cartographics,
    );
    return updated.map((c) => c.height);
  }

  /** 销毁地形管理器，恢复为椭球面并释放资源 */
  destroy(): void {
    if (this._viewer && !this._viewer.isDestroyed()) {
      // 恢复为最底层椭球面，避免悬空引用
      this._viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider();
    }
    this._initialized = false;
  }

  /** 内部工厂方法：根据配置创建 TerrainProvider */
  private _createProvider():
    | Cesium.TerrainProvider
    | Promise<Cesium.TerrainProvider> {
    switch (this._config.type) {
      case TerrainSourceType.CESIUM_ION: {
        // Cesium World Terrain：基于 ion 的全球地形，30m 精度
        // 原理：量化网格 (Quantized-Mesh) 格式，Cesium 内置支持异步加载
        const provider = Cesium.createWorldTerrainAsync({
          requestWaterMask: this._config.requestWaterMask ?? true,
          requestVertexNormals: this._config.requestVertexNormals ?? true,
        });
        return provider;
      }

      case TerrainSourceType.CUSTOM_URL: {
        // 自建 DEM 瓦片服务：企业级高精度地形
        // 部署方式：Cesium Terrain Builder (CTB) 生成 Quantized-Mesh 切片
        //           → 挂载到静态文件服务器或对象存储
        if (!this._config.url) {
          throw new Error(
            "[TerrainManager] CUSTOM_URL 模式下必须提供 url 参数",
          );
        }
        const provider = Cesium.createWorldTerrainAsync({
          requestWaterMask: this._config.requestWaterMask ?? false,
          requestVertexNormals: this._config.requestVertexNormals ?? false,
        });
        return provider;
      }

      case TerrainSourceType.ELLIPSOID:
      default: {
        // EllipsoidTerrainProvider：完美光滑椭球面
        // 所有点高度 = 0（相对于 WGS84 椭球面），无真实地形数据
        // 仅用于低配模式或离线无地形数据的场景
        return new Cesium.EllipsoidTerrainProvider();
      }
    }
  }
}
