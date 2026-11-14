import { ref, onBeforeUnmount } from "vue";
import { io, Socket } from "socket.io-client";
import type { RouteFlyWaypoint } from "@/stores/routeFlyData";
// 后端返回的航点格式（order 从后端带过来）
interface ServerWaypoint {
  lng: number;
  lat: number;
  altitude: number;
  order: number;
}

interface PlanRouteResponse {
  success: boolean;
  waypoints: ServerWaypoint[];
  message: string;
  warnings?: string[];
}
/**
 * WebSocket 通信钩子
 *
 * 职责（遵循 SKILL.md 前端桥接层规范）：
 *   1. 管理 socket.io 连接生命周期（连接/断开/重连）
 *   2. 封装路径规划请求 → 返回 Promise，方便 UI 层调用
 *   3. 不包含任何 Cesium 渲染逻辑
 */

export function useDroneSocket() {
  // 响应式状态，供 UI 层显示连接状态
  const isConnected = ref(false);
  const connectionError = ref<string | null>(null);

  let socket: Socket | null = null;
  /**
   * 建立 WebSocket 连接
   * 连接到后端 NestJS 的 /uav 命名空间
   */
  const connect = (): void => {
    if (socket?.connected) return;
    socket = io("http://localhost:3000/uav", {
      transports: ["websocket"], // 强制使用 WebSocket，不降级到轮询
      reconnection: true, // 断线自动重连
      reconnectionAttempts: 5, // 最多重连 5 次
      reconnectionDelay: 1000, // 重连间隔 1 秒
    });
    // 连接成功
    socket.on("connect", () => {
      console.log("[DroneSocket] WebSocket 已连接");
      isConnected.value = true;
      connectionError.value = null;
    });

    // 连接断开
    socket.on("disconnect", (reason) => {
      console.log(`[DroneSocket] WebSocket 断开: ${reason}`);
      isConnected.value = false;
    });

    // 连接失败
    socket.on("connect_error", (err) => {
      console.error(`[DroneSocket] 连接失败: ${err.message}`);
      connectionError.value = err.message;
    });
  };
  /**
   * 断开 WebSocket 连接
   */
  const disconnect = (): void => {
    socket?.disconnect();
    socket = null;
    isConnected.value = false;
  };
  /**
   * 发送路径规划请求，返回 Promise
   * @param waypoints 前端绘制的原始航点（不含 order）
   * @returns 后端返回的带 order 的完整航线
   */
  const planRoute = (
    waypoints: { lng: number; lat: number; altitude: number }[],
  ): Promise<RouteFlyWaypoint[]> => {
    return new Promise((resolve, reject) => {
      if (!socket?.connected) {
        reject(new Error("WebSocket 未连接，请先启动后端服务"));
        return;
      }
      // 发送 'route:plan' 事件到后端
      socket.emit("route:plan", { waypoints });
      // 监听后端返回的 'route:result' 事件
      socket.once("route:result", (response: PlanRouteResponse) => {
        console.log("[DroneSocket] 收到航线结果:", response.message);

        if (!response.success) {
          reject(new Error(response.message));
          return;
        }

        // 转换后端返回的数据为前端 store 期望的格式
        const routeWaypoints: RouteFlyWaypoint[] = response.waypoints.map(
          (wp) => ({
            lng: wp.lng,
            lat: wp.lat,
            altitude: wp.altitude,
            order: wp.order,
          }),
        );

        resolve(routeWaypoints);
      });
    });
  };
  onBeforeUnmount(() => {
    disconnect();
  });
  return {
    isConnected,
    connectionError,
    connect,
    disconnect,
    planRoute,
  };
}
