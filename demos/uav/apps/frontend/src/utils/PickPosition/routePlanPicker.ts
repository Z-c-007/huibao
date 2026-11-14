import * as Cesium from "cesium";
import { BasePicker } from "@/utils/PickPosition/BasePicker";
import { RoutePlan } from "../RoutePlan/routePlan";

export class RoutePlanPicker extends BasePicker {
  private routePlan: RoutePlan;
  private dynamicLineEntity: Cesium.Entity | null = null;

  constructor(options: ConstructorParameters<typeof BasePicker>[0]) {
    super(options);
    this.routePlan = new RoutePlan(this.viewer);
  }
  /**
   * 获取当前路由计划
   * @returns 路由计划
   */
  public getRoutePlan(): RoutePlan {
    return this.routePlan;
  }
  /**
   * 获取当前路由计划的点
   * @returns 路由计划的点
   */
  public getPositions(): Cesium.Cartesian3[] {
    return this.routePlan.getPositions();
  }
  /**
   * 处理点添加
   * @param cartesian 点
   */
  protected handlePointAdded(cartesian: Cesium.Cartesian3): void {
    this.routePlan.addWaypoint(cartesian);
    this.initDynamicLine();
    this.onChange?.(this.routePlan.getPositions());
  }
  /**
   * 处理完成
   */
  protected handleFinish(): Cesium.Cartesian3[] {
    if (this.dynamicLineEntity) {
      this.viewer.entities.remove(this.dynamicLineEntity);
      this.dynamicLineEntity = null;
    }
    return this.routePlan.getPositions();
  }
  /**
   * 清理可视化
   */
  protected cleanupVisuals(): void {
    this.routePlan.destroy();
    if (this.dynamicLineEntity) {
      this.viewer.entities.remove(this.dynamicLineEntity);
      this.dynamicLineEntity = null;
    }
  }
  /**
   * 初始化动态线
   */
  private initDynamicLine(): void {
    if (this.dynamicLineEntity) return;

    const dynamicPositions = new Cesium.CallbackProperty(() => {
      const positions = this.routePlan.getPositions();
      if (this.activePoint) {
        return [...positions, this.activePoint];
      }
      return positions;
    }, false);

    this.dynamicLineEntity = this.viewer.entities.add({
      polyline: {
        positions: dynamicPositions,
        width: 3,
        material: new Cesium.PolylineDashMaterialProperty({
          color: Cesium.Color.CYAN,
          dashLength: 16.0,
        }),
        clampToGround: false,
      },
    });
  }
}
