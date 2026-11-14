import type { GeoPoint, RiskLevel } from "./common";

export type DroneStatus =
  | "idle"
  | "ready"
  | "executing"
  | "returning"
  | "warning"
  | "offline";

export interface Drone {
  id: string;
  code: string;
  name: string;
  model: string;
  status: DroneStatus;
  battery: number;
  signal: number;
  speed: number;
  heading: number;
  missionId: string | null;
  updatedAt: string;
  location: GeoPoint;
  riskLevel: RiskLevel;
}
