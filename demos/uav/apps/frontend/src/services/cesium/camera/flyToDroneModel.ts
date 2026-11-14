import * as Cesium from "cesium";
import { flyToBoundingSphere } from "./flyToBoundingSphere.ts";
import type { FlyToDroneModelOptions } from "./types.ts";

export function flyToDroneModel(
  viewer: Cesium.Viewer,
  model: Cesium.Model,
  options: FlyToDroneModelOptions = {},
): void {
  const {
    duration = 2,
    heading = 0,
    pitch = -30,
    rangeMultiplier = 2,
  } = options;

  const boundingSphere = model.boundingSphere;
  const range = boundingSphere.radius * rangeMultiplier;

  flyToBoundingSphere(viewer, boundingSphere, {
    duration,
    heading,
    pitch,
    range,
  });
}
