import * as Cesium from "cesium";
export interface WaypointProperties {
  type: "uav-waypoint";
  index: number;
  // 你还可以在这里扩展更多属性，例如：
  // altitude?: number;
  // action?: 'hover' | 'photo';
}
export class RoutePlan {
  private viewer: Cesium.Viewer;
  private waypointPositions: Cesium.Cartesian3[];
  private pointEntities: Cesium.Entity[];
  private routeLineEntity: Cesium.Entity | null;

  constructor(viewer: Cesium.Viewer) {
    this.viewer = viewer;
    this.waypointPositions = [];
    this.pointEntities = [];
    this.routeLineEntity = null;
    this.initRouteLine();
  }
  /**
   * 初始化路由线实体
   */
  private initRouteLine() {
    if (this.routeLineEntity) return;
    this.routeLineEntity = new Cesium.Entity({
      id: "routeLine",
      polyline: {
        positions: new Cesium.CallbackProperty(() => {
          return this.waypointPositions;
        }, false),
        width: 5,
        material: Cesium.Color.RED.withAlpha(0.5),
        clampToGround: false,
      },
    });
    this.viewer.entities.add(this.routeLineEntity);
  }
  /**
   * 添加一个航点
   * @param cartesian3Pos 笛卡尔空间直角坐标
   */
  public addWaypoint(cartesian3Pos: Cesium.Cartesian3): void {
    this.waypointPositions.push(cartesian3Pos);

    const pointEntity: Cesium.Entity = this.viewer.entities.add({
      position: new Cesium.CallbackPositionProperty((): Cesium.Cartesian3 => {
        return cartesian3Pos;
      }, false),
      point: {
        color: Cesium.Color.WHITE,
        pixelSize: 10,
        outlineColor: Cesium.Color.DODGERBLUE, // TS 中建议使用全大写的颜色常量
        outlineWidth: 3,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      // 3. TS 规范：使用 PropertyBag 存储自定义业务属性
      properties: new Cesium.PropertyBag({
        type: "uav-waypoint",
        index: this.waypointPositions.length - 1,
      } as WaypointProperties),
    });

    this.pointEntities.push(pointEntity);
  }

  /**
   * 获取所有航点坐标数据 (向外暴露只读数据，供提交后端或业务逻辑使用)
   */
  public getPositions(): Cesium.Cartesian3[] {
    return [...this.waypointPositions]; // 返回浅拷贝，防止外部直接修改原数组
  }

  /**
   * 清理实例与视图层资源
   */
  public destroy(): void {
    if (this.routeLineEntity) {
      this.viewer.entities.remove(this.routeLineEntity);
    }

    this.pointEntities.forEach((p) => this.viewer.entities.remove(p));

    this.waypointPositions = [];
    this.pointEntities = [];
    this.routeLineEntity = null;
  }
}
