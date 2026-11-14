// src/composables/usePathPlanner.ts
import { ref, onUnmounted } from "vue";
import type {
  AStarWaypoint,
  NoFlyZone,
  AStarConfig,
} from "@/utils/AStar3DPathPlanner";
export function usePathPlanner() {
  const isPlanning = ref(false); // 暴露出响应式的 loading 状态供 UI 使用
  let worker: Worker | null = null;

  // 维护一个任务池，用于将 postMessage 的回调和 Promise resolve 绑定
  const taskPool = new Map<string, { resolve: Function; reject: Function }>();

  // 惰性初始化 Worker (只有在第一次算路时才创建，节省内存)
  const initAStarWorker = () => {
    if (!worker) {
      // Vite 特有的 Worker 引入语法 (ESM Module)
      worker = new Worker(
        new URL("../worker/astar.worker.ts", import.meta.url),
        {
          type: "module",
        },
      );

      // 统一监听 Worker 返回结果
      worker.onmessage = (e: MessageEvent) => {
        console.log("e", e);

        const { taskId, success, path, error, costTime } = e.data;
        const task = taskPool.get(taskId);

        if (task) {
          if (success) {
            console.log(`[Worker] 规划完成，耗时: ${costTime.toFixed(2)}ms`);
            task.resolve(path);
          } else {
            task.reject(new Error(error || "规划失败，未找到路径"));
          }
          taskPool.delete(taskId); // 清理任务池
        }

        // 如果任务池空了，说明算完了
        if (taskPool.size === 0) isPlanning.value = false;
      };
    }
    return worker;
  };
  /**
   * 新增：A* 全路径避障方法
   * 传入整条路径 + 所有禁飞区 → 返回避障后的完整安全路径
   * @param path
   * @param zones
   * @param config
   * @returns
   */
  const avoidObstacles = async (
    path: AStarWaypoint[],
    zones: NoFlyZone[],
    config?: AStarConfig,
  ): Promise<AStarWaypoint[] | null> => {
    const w = initAStarWorker(); // 惰性初始化 astar.worker
    isPlanning.value = true;

    const taskId = `astar_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

    return new Promise((resolve, reject) => {
      taskPool.set(taskId, { resolve, reject });
      w.postMessage({ taskId, path, zones, config });
    });
  };
  // 组件销毁时，清理 Worker 释放内存 (防内存泄漏)
  onUnmounted(() => {
    if (worker) {
      worker.terminate();
      worker = null;
    }
  });

  return {
    isPlanning,
    avoidObstacles,
  };
}
