import * as Cesium from "cesium";
import type { SceneRuntimeOptions } from "./types";
import { defaultSceneOptions } from "./sceneOptions";

export function applySceneOptions(
  scene: Cesium.Scene,
  options: SceneRuntimeOptions = {},
) {
  const merged = {
    ...defaultSceneOptions,
    ...options,
  };

  scene.globe.depthTestAgainstTerrain = merged.depthTestAgainstTerrain ?? false;
  scene.postProcessStages.fxaa.enabled = merged.fxaa ?? false;
  scene.fog.enabled = merged.fogEnabled ?? false;
  scene.globe.showGroundAtmosphere = merged.groundAtmosphere ?? false;
  scene.globe.enableLighting = merged.globeLighting ?? false;
  scene.debugShowFramesPerSecond = merged.debugShowFramesPerSecond ?? true;
  if (scene.skyAtmosphere) {
    scene.skyAtmosphere.show = merged.skyAtmosphere ?? false;
  }
  if (merged.skyBox ?? false) {
    // 如果原本为 undefined，可能需要重新实例化，但通常只需确保它不为 undefined 即可显示
    // 若之前被设为 undefined，这里可能需要 new Cesium.SkyBox()，视具体需求而定
    // 简单处理：如果希望显示且当前为 undefined，则恢复默认或新建
    if (!scene.skyBox) {
      scene.skyBox = new Cesium.SkyBox({
        sources: {
          positiveX: "Cesium_1_px.jpg",
          negativeX: "Cesium_1_mx.jpg",
          positiveY: "Cesium_1_py.jpg",
          negativeY: "Cesium_1_my.jpg",
          positiveZ: "Cesium_1_pz.jpg",
          negativeZ: "Cesium_1_mz.jpg",
        },
      });
    }
  } else {
    scene.skyBox = undefined;
  }

  scene.screenSpaceCameraController.minimumZoomDistance =
    merged.minimumZoomDistance ?? 10;
  scene.screenSpaceCameraController.maximumZoomDistance =
    merged.maximumZoomDistance ?? 20000000;

  if (scene.requestRenderMode) {
    scene.maximumRenderTimeChange = merged.maximumRenderTimeChange ?? Infinity;
  }

  return scene;
}
