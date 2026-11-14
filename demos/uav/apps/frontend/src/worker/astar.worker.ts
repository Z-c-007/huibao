import { AStar3DPathPlanner } from "@/utils/AStar3DPathPlanner";
import type {
  AStarWaypoint,
  NoFlyZone,
  AStarConfig,
} from "@/utils/AStar3DPathPlanner";
// ─── 消息协议定义 ────────────────────────────────
// 主线程 → Worker（请求）
interface AvoidObstacleRequest {
  taskId: string;
  path: AStarWaypoint[]; // 用户规划的原始航点序列
  zones: NoFlyZone[]; // 电子围栏转化后的禁飞区
  config?: AStarConfig; // 算法参数（分辨率、最大迭代等）
}

// Worker → 主线程（响应）
interface AvoidObstacleResponse {
  taskId: string;
  success: boolean;
  path: AStarWaypoint[] | null;
  error?: string;
  costTime: number;
}
//消息入口
self.onmessage = (e: MessageEvent<AvoidObstacleRequest>) => {
  const { taskId, path, zones, config } = e.data;
  const startTime = performance.now();
  try {
    const planner = new AStar3DPathPlanner({
      gridResolution: config?.gridResolution ?? 50,
      maxIterations: config?.maxIterations ?? 50000,
    });
    planner.setNoFlyZones(zones);
    // 核心：对原始路径逐段避障

    const safePath = segmentAvoid(planner, path);
    console.log("worker中的safePath", safePath);

    self.postMessage({
      taskId,
      success: safePath !== null,
      path: safePath,
      error: safePath === null ? "规划失败，未找到可行路径" : undefined,
      costTime: performance.now() - startTime,
    } satisfies AvoidObstacleResponse);
  } catch (error: unknown) {
    // 异常兜底：Worker 崩溃不会让主线程死等
    const message = error instanceof Error ? error.message : String(error);
    self.postMessage({
      taskId,
      success: false,
      path: null,
      error: message,
      costTime: performance.now() - startTime,
    } satisfies AvoidObstacleResponse);
  }
};
/**
 * // ─── 避障编排：将长路径拆成相邻航点对，逐段跑 A* ──────
 * 数学原理：A* 在相邻两点间搜索局部最优路径，
 * 避开中间的禁飞区后拼接成完整安全路径
 * @param planner
 * @param path
 */
function segmentAvoid(
  planner: AStar3DPathPlanner,
  path: AStarWaypoint[],
): AStarWaypoint[] | null {
  console.log("worker中segmentAvoid传入的path", path);

  if (path.length < 2) return null;

  const allWaypoints: AStarWaypoint[] = [];
  for (let i = 0; i < path.length - 1; i++) {
    const from = path[i]!;
    const to = path[i + 1]!;

    const result = planner.planPath(from, to);
    console.log("worker中传入的result", result);

    // 任何一段找不到路径 → 整条路径不可行
    if (!result.success || !result.path || result.path.length < 2) {
      // 两航点在当前网格分辨率下重合 → 保留原始航点对即可
      const segment = i === 0 ? [from, to] : [to];
      allWaypoints.push(...segment);
      continue; // 不 return null
    }

    // 拼接：第一段保留全部节点，后续段去掉起点（避免重复）
    const segment = i === 0 ? result.path : result.path.slice(1);
    console.log("worker中传入的segment", segment);

    allWaypoints.push(...segment);
  }

  return allWaypoints;
}
