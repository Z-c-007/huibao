import * as Cesium from "cesium";
import type { AddDroneModelOptions, DroneModelResult } from "./types.ts";

export async function addDroneModel(
  viewer: Cesium.Viewer,
  options: AddDroneModelOptions,
): Promise<DroneModelResult> {
  const {
    url,
    longitude,
    latitude,
    height,
    scale = 1,
    minimumPixelSize = 128,
    allowPicking = true,
    asynchronous = true,
  } = options;

  const position = Cesium.Cartesian3.fromDegrees(longitude, latitude, height);
  const modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(position);

  const model = await Cesium.Model.fromGltfAsync({
    url,
    modelMatrix,
    scale,
    minimumPixelSize,
    allowPicking,
    asynchronous,
  });

  viewer.scene.primitives.add(model);

  return {
    model,
    position,
    modelMatrix,
  };
}
