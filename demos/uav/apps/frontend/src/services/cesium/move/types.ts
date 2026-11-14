export interface FlightWaypoint {
  lng: number;
  lat: number;
  altitude: number;
  order: number;
}

export interface FlightControllerOptions {
  modelUrl: string;
  scale?: number;
  minimumPixelSize?: number;
  cruiseSpeed?: number;
  speed?: number;
  loop?: boolean;
  heightOffset?: number;
  showPath?: boolean;
  followMode?: boolean;
  fixedPixelSize?: boolean;
}

export interface FlightCallbacks {
  onStart?: () => void;
  onWaypointReach?: (waypoint: FlightWaypoint, index: number) => void;
  onComplete?: () => void;
  onStop?: () => void;
}
