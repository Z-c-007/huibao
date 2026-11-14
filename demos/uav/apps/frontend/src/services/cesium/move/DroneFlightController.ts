import * as Cesium from "cesium";
import type {
  FlightWaypoint,
  FlightControllerOptions,
  FlightCallbacks,
} from "./types";

const DEFAULTS = {
  scale: 1,
  minimumPixelSize: 128,
  cruiseSpeed: 80,
  speed: 1,
  loop: false,
  heightOffset: 0,
  showPath: true,
  followMode: true,
  fixedPixelSize: true,
} as const;

export class DroneFlightController {
  private viewer: Cesium.Viewer;
  private options: Required<FlightControllerOptions>; // 飞行控制器选项
  private entity: Cesium.Entity | null = null; // 飞行实体
  private positionProperty: Cesium.SampledPositionProperty; // 位置属性
  private orientationProperty: Cesium.VelocityOrientationProperty; // 朝向属性
  private callbacks: FlightCallbacks = {}; // 回调函数
  private waypoints: FlightWaypoint[] = []; // 航点
  private waypointTimes: Cesium.JulianDate[] = []; // 航点时间
  private previousWaypointIndex = -1; // 上一个航点索引
  private removePreUpdate: (() => void) | null = null; // 移除预更新函数
  private startTime!: Cesium.JulianDate; // 开始时间
  private finalTime!: Cesium.JulianDate; // 结束时间
  private referenceDistance: number = 0; // 参考距离
  private _isFlying = false; // 是否飞行中
  private _isPaused = false; // 是否暂停
  /**
   * 是否飞行中
   */
  get isFlying() {
    return this._isFlying;
  }
  /**
   * 是否暂停
   */
  get isPaused() {
    return this._isPaused;
  }
  /**
   * 获取当前航点索引
   */
  get currentWaypointIndex(): number {
    return this.previousWaypointIndex < 0 ? 0 : this.previousWaypointIndex + 1;
  }
  /**
   * 获取当前进度
   */
  get progress(): number {
    if (!this._isFlying || !this.startTime || !this.finalTime) return 0;
    const current = this.viewer.clock.currentTime;
    const elapsed = Cesium.JulianDate.secondsDifference(
      current,
      this.startTime,
    );
    const total = Cesium.JulianDate.secondsDifference(
      this.finalTime,
      this.startTime,
    );
    return Cesium.Math.clamp(elapsed / total, 0, 1);
  }
  /**
   * 构造函数
   *  * @param {Cesium.Viewer} viewer Cesium 视图器
   * @param {FlightControllerOptions} options 飞行控制器选项
   */
  constructor(viewer: Cesium.Viewer, options: FlightControllerOptions) {
    this.viewer = viewer;
    this.options = {
      modelUrl: options.modelUrl,
      scale: options.scale ?? DEFAULTS.scale,
      minimumPixelSize: options.minimumPixelSize ?? DEFAULTS.minimumPixelSize,
      cruiseSpeed: options.cruiseSpeed ?? DEFAULTS.cruiseSpeed,
      speed: options.speed ?? DEFAULTS.speed,
      loop: options.loop ?? DEFAULTS.loop,
      heightOffset: options.heightOffset ?? DEFAULTS.heightOffset,
      showPath: options.showPath ?? DEFAULTS.showPath,
      followMode: options.followMode ?? DEFAULTS.followMode,
      fixedPixelSize: options.fixedPixelSize ?? DEFAULTS.fixedPixelSize,
    };
    this.positionProperty = new Cesium.SampledPositionProperty();
    this.orientationProperty = new Cesium.VelocityOrientationProperty(
      this.positionProperty,
    );
  }
  /**
   * 执行飞行
   */
  fly(waypoints: FlightWaypoint[], callbacks?: FlightCallbacks): void {
    this.stop();
    this.callbacks = callbacks ?? {};
    this.waypoints = [...waypoints].sort((a, b) => a.order - b.order);
    this.previousWaypointIndex = -1;
    this.referenceDistance = 0;
    if (this.waypoints.length < 2) {
      console.warn("[DroneFlightController] 至少需要 2 个航点才能执行飞行");
      return;
    }
    this.buildFlightPath();
    this.createDroneEntity();
    this.setupClock();
    this.setupPreUpdate();
    // this.followDrone();

    this._isFlying = true;
    this._isPaused = false;
    this.callbacks.onStart?.();
  }
  /**
   * 暂停飞行
   */
  pause(): void {
    if (!this._isFlying || this._isPaused) return;
    this._isPaused = true;
    this.viewer.clock.shouldAnimate = false;
  }
  /**
   * 继续飞行
   */
  resume(): void {
    if (!this._isFlying || !this._isPaused) return;
    this._isPaused = false;
    this.viewer.clock.shouldAnimate = true;
  }
  /**
   * 停止飞行
   */
  stop(): void {
    if (!this._isFlying && this.previousWaypointIndex === -1) return;
    this._isFlying = false;
    this._isPaused = false;
    this.viewer.clock.shouldAnimate = false;
    this.viewer.clock.multiplier = 0;
    this.callbacks.onStop?.();
  }
  /**
   * 设置飞行速度
   */
  setSpeed(speed: number): void {
    this.options.speed = Math.max(0.1, speed);
    if (this._isFlying) {
      this.viewer.clock.multiplier = this.options.speed;
    }
  }
  /**
   * 销毁飞行控制器
   */
  destroy(): void {
    this.removePreUpdate?.();
    this.removePreUpdate = null;
    this.stop();
    if (this.entity) {
      this.viewer.entities.remove(this.entity);
      this.entity = null;
    }
    if (this.viewer.trackedEntity === this.entity) {
      this.viewer.trackedEntity = undefined;
    }
    this.positionProperty = new Cesium.SampledPositionProperty();
    this.orientationProperty = new Cesium.VelocityOrientationProperty(
      this.positionProperty,
    );
  }
  /**
   * 创建无人机实体
   */
  private createDroneEntity(): void {
    if (this.entity) {
      this.viewer.entities.remove(this.entity);
      this.entity = null;
    }

    this.entity = this.viewer.entities.add({
      position: this.positionProperty,
      orientation: this.orientationProperty,
      model: {
        uri: this.options.modelUrl,
        scale: this.options.scale,
        minimumPixelSize: this.options.fixedPixelSize
          ? 0
          : this.options.minimumPixelSize,
      },
      path: this.options.showPath
        ? {
            resolution: 1,
            material: new Cesium.PolylineGlowMaterialProperty({
              color: Cesium.Color.fromCssColorString("#00BFFF").withAlpha(0.6),
              glowPower: 0.15,
            }),
            width: 3,
            leadTime: 5,
            trailTime: 30,
          }
        : undefined,
      point: {
        pixelSize: 12,
        color: Cesium.Color.LIME.withAlpha(0.9),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: "🛸 无人机",
        font: "18px sans-serif",
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        pixelOffset: new Cesium.Cartesian2(0, -20),
        scaleByDistance: new Cesium.NearFarScalar(50, 1.0, 5000, 2.5),
        translucencyByDistance: new Cesium.NearFarScalar(100, 0.2, 500, 1.0),
      },
      ellipsoid: {
        radii: new Cesium.Cartesian3(25, 25, 25),
        material: Cesium.Color.LIME.withAlpha(0.12),
        outline: true,
        outlineColor: Cesium.Color.LIME.withAlpha(0.4),
        outlineWidth: 2,
      },
    });
  }
  /**
   * 构建飞行路径
   */
  private buildFlightPath(): void {
    // SampledPositionProperty 用于存储无人机的飞行路径
    this.positionProperty = new Cesium.SampledPositionProperty();
    this.orientationProperty = new Cesium.VelocityOrientationProperty(
      this.positionProperty,
    );
    this.waypointTimes = [];

    const positions = this.waypoints.map((wp) =>
      Cesium.Cartesian3.fromDegrees(
        wp.lng,
        wp.lat,
        wp.altitude + this.options.heightOffset,
      ),
    );

    const segmentDistances: number[] = [];
    let totalDistance = 0;

    for (let i = 1; i < positions.length; i++) {
      const dist = Cesium.Cartesian3.distance(positions[i - 1]!, positions[i]!);
      segmentDistances.push(dist);
      totalDistance += dist;
    }

    if (totalDistance < 0.01) {
      console.warn("[DroneFlightController] 航点间距过近，无法飞行");
      return;
    }

    const totalTime = totalDistance / this.options.cruiseSpeed;
    this.startTime = Cesium.JulianDate.now();
    this.finalTime = Cesium.JulianDate.addSeconds(
      this.startTime,
      totalTime,
      new Cesium.JulianDate(),
    );

    this.positionProperty.addSample(this.startTime, positions[0]!);

    const reusableDate = new Cesium.JulianDate();
    let cumulativeDistance = 0;

    for (let i = 1; i < positions.length; i++) {
      cumulativeDistance += segmentDistances[i - 1]!;
      const fraction = cumulativeDistance / totalDistance;
      const offset = totalTime * fraction;
      Cesium.JulianDate.addSeconds(this.startTime, offset, reusableDate);
      const sampleTime = Cesium.JulianDate.clone(reusableDate);
      this.positionProperty.addSample(sampleTime, positions[i]!);
      this.waypointTimes.push(sampleTime);
    }

    this.positionProperty.setInterpolationOptions({
      interpolationAlgorithm: Cesium.HermitePolynomialApproximation,
      interpolationDegree: 1,
    });
  }
  /**
   * 设置时钟
   */
  private setupClock(): void {
    const clock = this.viewer.clock;
    clock.shouldAnimate = true;
    clock.startTime = this.startTime.clone();
    clock.stopTime = this.finalTime.clone();
    clock.currentTime = this.startTime.clone();
    clock.multiplier = this.options.speed;
    clock.clockRange = this.options.loop
      ? Cesium.ClockRange.LOOP_STOP
      : Cesium.ClockRange.CLAMPED;
  }
  /**
   * 设置预更新事件
   */
  private setupPreUpdate(): void {
    this.removePreUpdate?.();
    this.removePreUpdate = this.viewer.scene.preUpdate.addEventListener(() => {
      if (!this._isFlying || this._isPaused) return;

      const currentTime = this.viewer.clock.currentTime;
      this.detectWaypointPassing(currentTime);
      if (this.options.fixedPixelSize) {
        this.updateModelScale();
      }
      if (
        !this.options.loop &&
        Cesium.JulianDate.greaterThanOrEquals(currentTime, this.finalTime)
      ) {
        this.completeFlight();
      }
    });
  }
  /**
   * 动态调整模型 scale，使其在屏幕上保持恒定的视觉大小
   */
  private updateModelScale(): void {
    if (!this.entity?.model) return;
    const current = this.viewer.clock.currentTime;
    const position = this.positionProperty.getValue(current);
    if (!position) return;
    const distance = Cesium.Cartesian3.distance(
      this.viewer.camera.positionWC,
      position,
    );
    if (this.referenceDistance === 0) {
      this.referenceDistance = Math.max(distance, 1);
    }
    const newScale = this.options.scale * (distance / this.referenceDistance);
    this.entity.model.scale = new Cesium.ConstantProperty(
      Cesium.Math.clamp(newScale, 0.05, 200),
    );
  }
  /**
   * 检测航点通过
   */
  private detectWaypointPassing(currentTime: Cesium.JulianDate): void {
    for (
      let i = this.previousWaypointIndex + 1;
      i < this.waypointTimes.length;
      i++
    ) {
      if (
        Cesium.JulianDate.greaterThanOrEquals(
          currentTime,
          this.waypointTimes[i]!,
        )
      ) {
        this.previousWaypointIndex = i;
        this.callbacks.onWaypointReach?.(this.waypoints[i + 1]!, i + 1);
      }
    }
  }
  /**
   * 跟随无人机
   */
  private followDrone(): void {
    if (!this.entity) return;
    this.entity.position = this.positionProperty;
    this.entity.orientation = this.orientationProperty;
    if (this.options.followMode) {
      this.viewer.trackedEntity = this.entity;
    }
  }
  /**
   * 完成飞行
   */
  private completeFlight(): void {
    this._isFlying = false;
    this.callbacks.onComplete?.();
  }
}
