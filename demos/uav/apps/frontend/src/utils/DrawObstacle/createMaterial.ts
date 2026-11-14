import * as Cesium from "cesium";
import type { ElectronicFenceOptions } from "./types";
import { hexToColor } from "./utils";

/**
 * 创建填充外观（基于 EllipsoidSurfaceAppearance）
 */
export function createFillAppearance(
  options: ElectronicFenceOptions,
): Cesium.EllipsoidSurfaceAppearance {
  const color = hexToColor(
    options.fillColor || "#00ff00",
    options.fillOpacity ?? 0.3,
  );
  const material = Cesium.Material.fromType("Color", {
    color: color,
  });
  return new Cesium.EllipsoidSurfaceAppearance({
    aboveGround: true,
    material,
  });
}

// /**
//  * 创建边框外观（基于 PerInstanceColorAppearance）
//  */
// export function createStrokeAppearance(
//   options: ElectronicFenceOptions,
// ): Cesium.PerInstanceColorAppearance {
//   return new Cesium.PerInstanceColorAppearance({
//     flat: true,
//     renderState: {
//       lineWidth: options.strokeWidth || 2,
//     },
//   });
// }
