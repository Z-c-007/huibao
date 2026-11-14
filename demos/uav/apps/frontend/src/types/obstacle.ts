import type { GeoPoint, RiskLevel } from "./common";

export type ObstacleType = "building" | "no-fly-zone" | "limit-zone" | "temporary";

export interface ObstacleZone {
  id: string;
  name: string;
  type: ObstacleType;
  riskLevel: RiskLevel;
  minAltitude: number;
  maxAltitude: number;
  activeTime: string;
  center: GeoPoint;
  remark: string;
}
