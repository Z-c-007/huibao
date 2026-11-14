import * as Cesium from "cesium";
import type { ElectronicFenceOptions } from "./types";
import { lngLatsToCartesian3 } from "./utils";

/**
 * 创建填充几何实例
 */
export function createFillGeometry(
  options: ElectronicFenceOptions,
): Cesium.GeometryInstance {
  const positions = lngLatsToCartesian3(options.coordinates);
  const baseHeight = Number(options.coordinates[0]?.[2]) || 0;
  const fenceHeight = Number(options.height) || 0.1;
  const geometry = new Cesium.PolygonGeometry({
    polygonHierarchy: new Cesium.PolygonHierarchy(positions),
    // perPositionHeight: true, 是放弃统一高度，使用每个坐标点自带的 Z 值高度
    height: baseHeight, // 底部紧贴真实的地理模型海拔
    extrudedHeight: baseHeight + fenceHeight, // 顶部海拔 = 底部海拔 + 拉伸高度
    vertexFormat: Cesium.EllipsoidSurfaceAppearance.VERTEX_FORMAT,
  });

  return new Cesium.GeometryInstance({
    geometry,
    id: options.id,
  });
}
// /**
//  * 创建边框几何实例（带颜色属性）
//  */
// export function createStrokeGeometry(
//   options: ElectronicFenceOptions,
// ): Cesium.GeometryInstance {
//   const positions = lngLatsToCartesian3(options.coordinates);
//   const color = hexToColor(
//     options.strokeColor || "#ff0000",
//     options.strokeOpacity ?? 1,
//   );
//   const geometry = new Cesium.PolygonOutlineGeometry({
//     polygonHierarchy: new Cesium.PolygonHierarchy(positions),
//   });
//   return new Cesium.GeometryInstance({
//     geometry: geometry,
//     id: generateUniqueID(),
//     attributes: {
//       color: Cesium.ColorGeometryInstanceAttribute.fromColor(color),
//     },
//   });
// }
