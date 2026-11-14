import * as Cesium from "cesium";
import { BasePicker } from "./BasePicker";

export class GeofencePicker extends BasePicker {
  private points: Cesium.Cartesian3[] = [];
  private lineEntity: Cesium.Entity | null = null;
  private renderPoints: Cesium.Cartesian3[] = [];

  public updateHeight(targetHeight: number): void {
    if (this.points.length === 0) return;
    this.points = this.points.map((cartesian) => {
      const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
      cartographic.height = targetHeight;
      return Cesium.Cartographic.toCartesian(cartographic);
    });
    this.onChange?.([...this.points]);
  }

  public getPoints(): Cesium.Cartesian3[] {
    return [...this.points];
  }

  protected handlePointAdded(cartesian: Cesium.Cartesian3): void {
    this.points.push(cartesian);
    this.initEntities();
    this.onChange?.([...this.points]);
  }

  protected handleFinish(): Cesium.Cartesian3[] {
    return [...this.points];
  }

  protected cleanupVisuals(): void {
    this.points = [];
    if (this.lineEntity) this.viewer.entities.remove(this.lineEntity);
    this.lineEntity = null;
  }

  private initEntities(): void {
    if (this.lineEntity) return;

    const dynamicPositions = new Cesium.CallbackProperty(() => {
      this.renderPoints.length = 0;
      for (let i = 0; i < this.points.length; i++) {
        this.renderPoints.push(this.points[i] as Cesium.Cartesian3);
      }
      if (this.handler && this.activePoint) {
        this.renderPoints.push(this.activePoint);
      }
      if (this.renderPoints.length >= 3) {
        this.renderPoints.push(this.renderPoints[0] as Cesium.Cartesian3);
      }
      return this.renderPoints;
    }, false);

    this.lineEntity = this.viewer.entities.add({
      polyline: {
        positions: dynamicPositions,
        width: 3,
        material: new Cesium.PolylineDashMaterialProperty({
          color: Cesium.Color.CYAN,
          dashLength: 20.0,
        }),
        clampToGround: false,
      },
    });
  }
}
