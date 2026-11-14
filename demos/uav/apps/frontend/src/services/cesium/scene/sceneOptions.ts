import type { SceneRuntimeOptions } from "./types";

export const defaultSceneOptions: Required<SceneRuntimeOptions> = {
  depthTestAgainstTerrain: false, //地形对图元的深度测试
  fxaa: false, //抗锯齿
  showSkyBox: false, //天空盒
  showSkyAtmosphere: false, //天空大气
  showGroundAtmosphere: false, //地面大气
  showGlobeLighting: false, //地球光照
  fogEnabled: false, //雾
  groundAtmosphere: false, //地面大气
  globeLighting: false, //地球光照
  skyAtmosphere: false, //天空大气
  skyBox: false, //天空盒
  maximumRenderTimeChange: Infinity, //最大渲染时间变化
  minimumZoomDistance: 10, //最小缩放距离
  maximumZoomDistance: 20000000, //最大缩放距离
  debugShowFramesPerSecond: true, //帧率显示
};
