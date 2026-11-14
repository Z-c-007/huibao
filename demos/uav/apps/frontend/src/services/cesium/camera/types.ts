import type * as Cesium from "cesium";

export interface FlyToBoundingSphereOptions {
  duration?: number;
  heading?: number;
  pitch?: number;
  range?: number;
}

export interface FlyToDroneModelOptions {
  duration?: number;
  heading?: number;
  pitch?: number;
  rangeMultiplier?: number;
}

export interface FlyToPositionOptions {
  duration?: number;
  heading?: number;
  pitch?: number;
  range?: number;
}

export type CameraTargetPosition = Cesium.Cartesian3;
