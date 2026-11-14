import * as Cesium from "cesium";

export const defaultViewerOptions: Cesium.Viewer.ConstructorOptions = {
  animation: false, // 动画
  timeline: false, // 时间轴
  baseLayerPicker: false, // 图层选择器
  geocoder: false, // 搜索框
  homeButton: false, // 首页按钮
  sceneModePicker: false, // 场景模式选择器
  navigationHelpButton: false, // 导航帮助按钮
  fullscreenButton: false, // 全屏按钮
  infoBox: false, // 信息框
  selectionIndicator: false, // 选择指示器
  shouldAnimate: true, // 应该动画
  // requestRenderMode: true, // 按需渲染
  // maximumRenderTimeChange:, // 静止时永不渲染
};
