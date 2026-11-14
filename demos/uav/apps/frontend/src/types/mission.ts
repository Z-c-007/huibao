import type { GeoPoint } from "./common";

export type MissionStatus =
  | "draft"
  | "planned"
  | "pending"
  | "executing"
  | "paused"
  | "completed";

export interface Waypoint extends GeoPoint {
  id: string;
  order: number;
  action: string;
  stayTime: number;
}

export interface Mission {
  id: string;
  code: string;
  name: string;
  type: string;
  status: MissionStatus;
  droneId: string | null;
  priority: "P0" | "P1" | "P2";
  startTime: string;
  estimatedDurationMinutes: number;
  totalDistanceKm: number;
  waypoints: Waypoint[];
  remark: string;
}
