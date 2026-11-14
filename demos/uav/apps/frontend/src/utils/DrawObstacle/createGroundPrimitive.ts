import * as Cesium from "cesium";
import type { ElectronicFenceOptions } from "./types";
import { createFillGeometry } from "./createGeometry";
import { createFillAppearance } from "./createMaterial";
import { lngLatsToCartesian3, hexToColor } from "./utils";
export interface ElectronicFenceCreateResult {
  instance: ElectronicFence; // Cesium 实例对象（用于后续 show/hide/destroy）
  fenceOptions: ElectronicFenceOptions; // 纯数据对象（用于存 store）
}
export class ElectronicFence {
  private viewer: Cesium.Viewer;
  public options: ElectronicFenceOptions;
  private fillPrimitive: Cesium.Primitive | null = null;
  private strokeEntity: Cesium.Entity | null = null;
  constructor(viewer: Cesium.Viewer, options: ElectronicFenceOptions) {
    this.viewer = viewer;
    this.options = {
      fillColor: "#00ff00",
      fillOpacity: 0.3,
      strokeColor: "#ff0000",
      strokeOpacity: 1,
      strokeWidth: 2,
      show: true,
      ...options,
    };
    this.init();
  }
  /**
   * 初始化：创建几何实例和外观，并添加到场景中
   */
  private async init(): Promise<void> {
    // 关键：先初始化地形高度
    this.createFillPrimitive();
    this.createStrokePrimitive();
    // this.updateShow();
  }
  /**
   * 创建填充和边框的 Primitive
   */
  private createFillPrimitive(): void {
    const geometry = createFillGeometry(this.options);
    const appearance = createFillAppearance(this.options);
    this.fillPrimitive = new Cesium.Primitive({
      geometryInstances: geometry,
      appearance,
      asynchronous: false,
    });
    this.viewer.scene.primitives.add(this.fillPrimitive);
  }
  /**
   * 创建边框 Primitive（使用 PerInstanceColorAppearance 以支持颜色属性）
   */
  private createStrokePrimitive(): void {
    const positions = lngLatsToCartesian3(this.options.coordinates);
    // 闭合多边形
    positions.push(positions[0] as Cesium.Cartesian3);
    // 添加前，强制清除同名 ID 的残余 Entity
    this.viewer.entities.removeById(this.options.id);
    this.strokeEntity = this.viewer.entities.add({
      id: this.options.id,
      polyline: {
        positions,
        width: this.options.strokeWidth || 2,
        material: new Cesium.ColorMaterialProperty(
          hexToColor(
            this.options.strokeColor || "#ff0000",
            this.options.strokeOpacity ?? 1,
          ),
        ),
        // 启用地形贴合
        clampToGround: true,
      },
    });
  }

  /** 更新电子围栏 */
  // update(options: ElectronicFenceUpdateOptions): void {
  //   this.options = { ...this.options, ...options };
  //   this.destroyPrimitives();
  //   this.init();
  // }
  /**
   * 更新显示状态（show/hide）
   */
  private updateShow(): void {
    const show = this.options.show ?? true;
    this.fillPrimitive && (this.fillPrimitive.show = show);
    this.strokeEntity && (this.strokeEntity.show = show);
  }
  /**
   * 销毁实例，清理内存
   */
  destroy(): void {
    // ✨ 修复 4：Primitive 和 Entity 必须分开使用各自的 API 销毁！
    if (this.fillPrimitive) {
      this.viewer.scene.primitives.remove(this.fillPrimitive);
      this.fillPrimitive = null;
    }
    if (this.strokeEntity) {
      this.viewer.entities.remove(this.strokeEntity);
      this.strokeEntity = null;
    }
  }
}

/** 工厂函数：快速创建电子围栏 */
export function createElectronicFence(
  viewer: Cesium.Viewer,
  options: ElectronicFenceOptions,
): ElectronicFenceCreateResult {
  const instance = new ElectronicFence(viewer, options);
  return { instance, fenceOptions: options };
}
