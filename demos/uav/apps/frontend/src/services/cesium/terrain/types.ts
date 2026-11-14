import type * as Cesium from "cesium";

/** 地形数据源类型 */
export const TerrainSourceType = {
  /** 低配模式：光滑 WGS84 椭球面（无真实地形，建筑不贴地） */
  ELLIPSOID: "ellipsoid",
  /** Cesium World Terrain 在线服务（全球 30m 精度） */
  CESIUM_ION: "ion",
  /** 自定义地形瓦片服务（企业自建高精度 DEM） */
  CUSTOM_URL: "custom-url",
} as const;

export type TerrainSourceType =
  (typeof TerrainSourceType)[keyof typeof TerrainSourceType];

/** 地形管理器配置 */
export interface TerrainConfig {
  /** 地形数据源类型 */
  type: TerrainSourceType;
  /** Cesium Ion 资产 ID（type=ion 时必填） */
  ionAssetId?: number;
  /** 自定义瓦片服务 URL（type=custom-url 时必填） */
  url?: string;
  /** 最大地形精度层级：控制瓦片采样密度，近处精细远处粗糙 */
  maxLevel?: number;
  /** 是否请求水体遮罩 */
  requestWaterMask?: boolean;
  /** 是否请求顶点法线（启用地球光照时需开启） */
  requestVertexNormals?: boolean;
}

/** 地形管理器默认配置 */
export const DEFAULT_TERRAIN_CONFIG: Required<
  Omit<TerrainConfig, "ionAssetId" | "url">
> = {
  type: "ion",
  maxLevel: 15,
  requestWaterMask: true,
  requestVertexNormals: true,
};
