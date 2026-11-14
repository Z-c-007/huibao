export interface WaypointDTO {
  lng: number;
  lat: number;
  altitude: number;
}

export interface OrderedWaypointDTO extends WaypointDTO {
  order: number;
}

export interface PlanRouteDTO {
  waypoints: WaypointDTO[];
}

export interface PlanRouteResponse {
  success: boolean;
  waypoints: OrderedWaypointDTO[];
  message: string;
  warnings?: string[];
}
