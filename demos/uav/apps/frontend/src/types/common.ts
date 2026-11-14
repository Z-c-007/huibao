export interface GeoPoint {
  lng: number;
  lat: number;
  altitude: number;
}

export interface ListMeta {
  total: number;
  online?: number;
  warning?: number;
}

export type RiskLevel = "low" | "medium" | "high";
