import * as Cesium from "cesium";
import type { CameraTargetPosition, FlyToPositionOptions } from "./types.ts";

export function flyToPosition(
  viewer: Cesium.Viewer,
  position: CameraTargetPosition,
  options: FlyToPositionOptions = {},
): void {
  const {
    duration = 2,
    heading = 0,
    pitch = -30,
    range = 300,
  } = options;

  viewer.camera.flyTo({
    destination: position,
    duration,
    orientation: {
      heading: Cesium.Math.toRadians(heading),
      pitch: Cesium.Math.toRadians(pitch),
      roll: 0,
    },
  });

  viewer.camera.moveBackward(range);
}
