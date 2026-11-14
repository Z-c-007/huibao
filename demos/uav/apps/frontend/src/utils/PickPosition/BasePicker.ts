import * as Cesium from "cesium";
import { throttle } from "lodash-es";
import { pickCartesian } from "./pickCartesian.ts";

export interface BasePickerOptions<T> {
  viewer: Cesium.Viewer;
  onChange?: (positions: Cesium.Cartesian3[]) => void;
}
export abstract class BasePicker<T = Cesium.Cartesian3[]> {
  protected viewer: Cesium.Viewer;
  protected handler: Cesium.ScreenSpaceEventHandler | null = null;
  protected activePoint: Cesium.Cartesian3 | null = null;

  protected onChange?: (positions: Cesium.Cartesian3[]) => void;

  private _resolve?: (positions: Cesium.Cartesian3[]) => void;
  private _reject?: (reason?: any) => void;
  /**
   * 当前活跃会话的控制对象，包含 Promise 的 reject 方法和 Cesium 事件处理器
   */
  private _activeSession?: {
    reject: (reason?: unknown) => void;
    handler: Cesium.ScreenSpaceEventHandler;
  };
  constructor(options: BasePickerOptions<T>) {
    this.viewer = options.viewer;
    this.onChange = options.onChange;
  }
  /**
   * 开始拾取位置，返回一个 Promise，在用户完成拾取后 resolve 结果
   * @returns
   */
  public startAsync(): Promise<T> {
    this.stop(); // 先停掉上一次的 handler，同时 reject 上一个 Promise

    return new Promise<T>((resolve, reject) => {
      const handler = new Cesium.ScreenSpaceEventHandler(
        this.viewer.scene.canvas,
      );
      this._activeSession = { reject, handler };
      //LEFT_CLICK
      handler.setInputAction(
        (movement: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
          const cartesian = pickCartesian(this.viewer, movement.position);
          if (cartesian) {
            this.handlePointAdded(cartesian);
          }
        },
        Cesium.ScreenSpaceEventType.LEFT_CLICK,
      );
      //MOUSE_MOVE(throttle)
      handler.setInputAction(
        throttle((movement) => {
          const cartesian = pickCartesian(this.viewer, movement.endPosition);
          if (cartesian) this.activePoint = cartesian;
        }, 50),
        Cesium.ScreenSpaceEventType.MOUSE_MOVE,
      );
      //RIGHT_CLICK
      handler.setInputAction(() => {
        handler.destroy();
        this._activeSession = undefined;
        const res = this.handleFinish();
        resolve(res);
      }, Cesium.ScreenSpaceEventType.RIGHT_CLICK);
    });
  }
  /**
   * 显示取消
   */
  public cancel(): void {
    if (this._activeSession) {
      this._activeSession.handler.destroy();
      this._activeSession.reject(new Error("用户取消了位置拾取"));
      this._activeSession = undefined;
    }
    this.handler = null;
  }
  public stop(): void {
    this.activePoint = null;
    if (this.handler) {
      this.handler.destroy();
      this.handler = null;
    }
  }

  public clear(): void {
    this.stop();
    this.cleanupVisuals();
  }
  //#region 抽象方法，交由子类实现
  protected abstract handlePointAdded(cartesian: Cesium.Cartesian3): void;
  protected abstract handleFinish(): T;
  protected abstract cleanupVisuals(): void;
}
