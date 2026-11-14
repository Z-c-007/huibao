import * as Cesium from "cesium";
import type { FlyToBoundingSphereOptions } from "./types.ts";

export function flyToBoundingSphere(
  viewer: Cesium.Viewer,
  boundingSphere: Cesium.BoundingSphere,
  options: FlyToBoundingSphereOptions = {},
): void {
  const {
    duration = 2,
    heading = 0,
    pitch = -30,
    range = boundingSphere.radius * 2,
  } = options;

  viewer.camera.flyToBoundingSphere(boundingSphere, {
    duration,
    offset: new Cesium.HeadingPitchRange(
      Cesium.Math.toRadians(heading),
      Cesium.Math.toRadians(pitch),
      range,
    ),
  });
}
