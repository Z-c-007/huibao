import * as Cesium from "cesium";

export interface SceneRuntimeOptions {
  depthTestAgainstTerrain?: boolean; // 是否启用地形深度测试
  fxaa?: boolean; // 是否启用FXAA抗锯齿
  showSkyBox?: boolean; // 是否显示天空盒
  showSkyAtmosphere?: boolean; // 是否显示天空大气
  showGroundAtmosphere?: boolean; // 是否显示地面大气
  showGlobeLighting?: boolean; // 是否显示地球照明
  fogEnabled?: boolean; // 是否启用雾效
  groundAtmosphere?: boolean; // 是否显示地面大气
  globeLighting?: boolean; // 是否显示地球照明
  skyAtmosphere?: boolean; // 是否显示天空大气
  skyBox?: boolean; // 是否显示天空盒
  maximumRenderTimeChange?: number; // 最大渲染时间变化，单位为秒
  minimumZoomDistance?: number; // 最小缩放距离
  maximumZoomDistance?: number; // 最大缩放距离
  debugShowFramesPerSecond?: boolean; // 是否显示帧率统计
}

export interface CreateSceneOptions {
  sceneOptions?: SceneRuntimeOptions;
}
export type CesiumScene = Cesium.Scene;
