import * as Cesium from "cesium";

/**
 * 十六进制颜色转 Cesium.Color
 */
export function hexToColor(hex: string, alpha: number = 1): Cesium.Color {
  return Cesium.Color.fromCssColorString(hex).withAlpha(alpha);
}

/**
 * 经纬度+高度数组转 Cesium.Cartesian3 数组
 * @param coordinates 经 纬 高度
 * @returns Cesium.Cartesian3 数组
 */
export function lngLatsToCartesian3(
  coordinates: [number, number, number][],
): Cesium.Cartesian3[] {
  return coordinates.map(([lng, lat, height]) =>
    Cesium.Cartesian3.fromDegrees(lng, lat, height ?? 0),
  );
}
/**
 * Cesium.Cartesian3 数组转 经纬度+高度数组
 * @param coordinates Cesium.Cartesian3 数组
 * @returns 经 纬 高度
 */
export function cartesian3ToLngLats(
  coordinates: Cesium.Cartesian3[],
): [number, number, number][] {
  return coordinates.map((cartesian) => {
    // 1. 将笛卡尔坐标 (Cartesian3) 转换为弧度制的地理坐标 (Cartographic)
    const cartographic = Cesium.Cartographic.fromCartesian(cartesian);

    // 2. 将弧度 (Radians) 转换为熟悉的角度 (Degrees)
    const lng = Cesium.Math.toDegrees(cartographic.longitude);
    const lat = Cesium.Math.toDegrees(cartographic.latitude);
    const height = cartographic.height;

    return [lng, lat, height];
  });
}
