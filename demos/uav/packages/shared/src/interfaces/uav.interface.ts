//类型定义--前后端共享
/** 航点坐标 */
/** 单个航点坐标 */
export interface WaypointDTO {
  lng: number; // 经度 [-180, 180]
  lat: number; // 纬度 [-90, 90]
  altitude: number; // 海拔高度(米)
}
/** 路径规划请求 */
export interface PlanRouteRequest {
  waypoints: WaypointDTO[];
}

/** 后端返回的路径规划结果 */
export interface PlanRouteResponse {
  success: boolean;
  waypoints: (WaypointDTO & { order: number })[]; // 带顺序的航点
  message: string;
  warnings?: string[];
}

/** 围栏类型 */
export type FenceType = 'no-fly-zone' | 'limit-zone' | 'temporary';
/** 风险等级 */
export type FenceRiskLevel = 'low' | 'medium' | 'high';
/** 围栏顶点坐标 */
export interface FenceVertex {
  lng: number; // 经度 [-180, 180]
  lat: number; // 纬度 [-90, 90]
  altitude: number; // 海拔高度(米)
}
/** 电子围栏实体 */
export interface FenceEntity {
  id: string;
  name: string;
  type: FenceType;
  riskLevel: FenceRiskLevel;
  /** 多边形顶点数组，最后一个点自动闭合 */
  coordinates: FenceVertex[];
  /** 限制高度下限（米），无人机低于此高度可穿行 */
  minAltitude: number;
  /** 限制高度上限（米），无人机高于此高度可飞越 */
  maxAltitude: number;
  /** 生效时间描述，如 "永久" / "工作日08:00-18:00" */
  activeTime: string;
  /** 备注说明 */
  remark?: string;
  createdAt: string;
  updatedAt: string;
}
/** 创建围栏请求 */
export interface CreateFenceRequest {
  name: string;
  type: FenceType;
  riskLevel: FenceRiskLevel;
  coordinates: FenceVertex[];
  minAltitude: number;
  maxAltitude: number;
  activeTime?: string;
  remark?: string;
}
/** 更新围栏请求（所有字段可选） */
export interface UpdateFenceRequest {
  name?: string;
  type?: FenceType;
  riskLevel?: FenceRiskLevel;
  coordinates?: FenceVertex[];
  minAltitude?: number;
  maxAltitude?: number;
  activeTime?: string;
  remark?: string;
}
