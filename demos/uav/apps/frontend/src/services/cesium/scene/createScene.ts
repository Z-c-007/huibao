import * as Cesium from "cesium";
import { applySceneOptions } from "./applySceneOptions";
import type { CreateSceneOptions } from "./types";
export function createScene(
  viewer: Cesium.Viewer,
  options: CreateSceneOptions = {},
): Cesium.Scene {
  const scene = viewer.scene;
  applySceneOptions(scene, options.sceneOptions);
  return scene;
}
