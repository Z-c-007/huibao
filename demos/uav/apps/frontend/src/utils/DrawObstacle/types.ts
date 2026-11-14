export interface ElectronicFenceOptions {
  /** 唯一标识 */
  id: string;
  /** 经纬度坐标数组 [[lng, lat, height], [lng, lat, height], ...] */
  coordinates: [number, number, number][];
  /** 填充颜色（hex格式，如 '#ff0000'） */
  fillColor?: string;
  /** 填充透明度（0-1） */
  fillOpacity?: number;
  /** 边框颜色 */
  strokeColor?: string;
  /** 边框透明度 */
  strokeOpacity?: number;
  /** 边框宽度（像素） */
  strokeWidth?: number;
  /** 是否显示 */
  show?: boolean;
  height?: number; // 控制整个围栏的统一拉伸高度
}

export interface ElectronicFenceUpdateOptions {
  coordinates?: [number, number, number][];
  fillColor?: string;
  fillOpacity?: number;
  strokeColor?: string;
  strokeOpacity?: number;
  strokeWidth?: number;
  show?: boolean;
}
