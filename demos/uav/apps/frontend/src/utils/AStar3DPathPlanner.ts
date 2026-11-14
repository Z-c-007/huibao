/**
 * AStar3DPathPlanner — 3D A* 无人机航迹规划算法
 *
 * 架构层级：核心算法层（纯 TypeScript，脱离 DOM / Vue / Cesium 运行）
 * 职责：在三维空间中搜索避开禁飞区的最短路径
 *
 * 数据结构优化（vs 原始版）：
 *   BinaryHeap O(log n) 替代 Array.splice O(n) — 优先队列插入
 *   Set<string>    O(1)     替代 Array.some  O(n) — 闭表查重
 */

// 导出类型 — Worker 与桥接层的数据合同

/** 单个航点（经纬度 + 海拔） */
export interface AStarWaypoint {
  lat: number;
  lng: number;
  altitude: number;
}

/** 禁飞区包围盒（经纬度 + 高度范围的轴对齐矩形） */
export interface NoFlyZone {
  minLat: number;
  maxLat: number;
  minLng: number;
  maxLng: number;
  minAlt: number;
  maxAlt: number;
}

/** A* 算法配置项 */
export interface AStarConfig {
  gridResolution?: number;
  maxIterations?: number;
}

/** 路径统计信息 */
export interface PathStatistics {
  totalWaypoints: number;
  totalDistance: number;
  totalTime: number;
  totalTimeMinutes: number;
  maxAltitude: number;
  minAltitude: number;
  averageSpeed: number;
}

/** planPath() 返回结果 */
export interface PlanPathResult {
  success: boolean;
  path?: AStarWaypoint[];
  statistics?: PathStatistics;
  error?: string;
}

/** @deprecated 使用 AStarWaypoint 替代，保留以兼容旧引用 */
export type AStar3DPathPlannerPosition = AStarWaypoint;

// 内部数据结构

/** 3D 网格节点 */
class GridNode {
  x: number;
  y: number;
  z: number;
  lat: number;
  lng: number;
  altitude: number;
  g: number = 0;
  h: number = 0;
  f: number = 0;
  parent: GridNode | null = null;
  walkable: boolean = true;

  constructor(
    x: number,
    y: number,
    z: number,
    lat: number,
    lng: number,
    altitude: number,
  ) {
    this.x = x;
    this.y = y;
    this.z = z;
    this.lat = lat;
    this.lng = lng;
    this.altitude = altitude;
  }

  updateF(): void {
    this.f = this.g + this.h;
  }
}

/**
 * 二叉堆（最小堆）— 优先队列
 *
 * 时间复杂度：
 *   插入 enqueue  O(log n)
 *   弹出 dequeue  O(log n)
 *
 * 实现原理：
 *   用数组存储完全二叉树，索引关系：
 *     父节点  parent = Math.floor((i - 1) / 2)
 *     左子节点 left   = i * 2 + 1
 *     右子节点 right  = i * 2 + 2
 *   堆顶（索引0）始终是 f 值最小的节点 — A* 每次都扩展最优候选
 */
class BinaryHeap {
  private heap: GridNode[] = [];

  enqueue(node: GridNode): void {
    this.heap.push(node);
    this.bubbleUp(this.heap.length - 1);
  }

  dequeue(): GridNode | undefined {
    if (this.heap.length === 0) return undefined;
    const top = this.heap[0]!;
    const last = this.heap.pop()!;
    if (this.heap.length > 0) {
      this.heap[0] = last;
      this.sinkDown(0);
    }
    return top;
  }

  get size(): number {
    return this.heap.length;
  }

  isEmpty(): boolean {
    return this.heap.length === 0;
  }

  private bubbleUp(idx: number): void {
    while (idx > 0) {
      const parent = (idx - 1) >> 1;
      if (this.heap[idx]!.f >= this.heap[parent]!.f) break;
      [this.heap[idx], this.heap[parent]] = [
        this.heap[parent]!,
        this.heap[idx]!,
      ];
      idx = parent;
    }
  }

  private sinkDown(idx: number): void {
    const len = this.heap.length;
    while (true) {
      let smallest = idx;
      const left = (idx << 1) + 1;
      const right = left + 1;
      if (left < len && this.heap[left]!.f < this.heap[smallest]!.f)
        smallest = left;
      if (right < len && this.heap[right]!.f < this.heap[smallest]!.f)
        smallest = right;
      if (smallest === idx) break;
      [this.heap[idx], this.heap[smallest]] = [
        this.heap[smallest]!,
        this.heap[idx]!,
      ];
      idx = smallest;
    }
  }
}

// 3D 网格辅助类型

interface GridInfo {
  minLat: number;
  maxLat: number;
  minLng: number;
  maxLng: number;
  minAlt: number;
  maxAlt: number;
  gridX: number;
  gridY: number;
  gridZ: number;
}

interface GridData {
  grid: GridNode[][][];
  startNode: GridNode;
  endNode: GridNode;
  gridInfo: GridInfo;
}

// A* 算法主类

export class AStar3DPathPlanner {
  private gridResolution: number;
  private maxIterations: number;
  private noFlyZones: NoFlyZone[];

  constructor(options: AStarConfig = {}) {
    this.gridResolution = options.gridResolution ?? 50;
    this.maxIterations = options.maxIterations ?? 50000;
    this.noFlyZones = [];
  }

  /**
   * 规划 3D 路径（算法对外唯一入口）
   * @param start 起点
   * @param end   终点
   * @param options 覆盖配置项
   */
  planPath(
    start: AStarWaypoint,
    end: AStarWaypoint,
    options: AStarConfig = {},
  ): PlanPathResult {
    try {
      const gridData = this.create3DGrid(start, end, options);
      if (!gridData) {
        return { success: false, error: "Failed to create 3D grid" };
      }

      const { grid, startNode, endNode, gridInfo } = gridData;

      this.markNoFlyZones(grid, gridInfo);

      const path = this.findPathAStar(grid, startNode, endNode);
      if (!path || path.length === 0) {
        return { success: false, error: "No path found" };
      }

      const waypoints: AStarWaypoint[] = path.map((node) => ({
        lat: node.lat,
        lng: node.lng,
        altitude: node.altitude,
      }));

      const smoothedPath = this.smoothPath(waypoints);
      const statistics = this.calculateStatistics(smoothedPath);

      return { success: true, path: smoothedPath, statistics };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: message };
    }
  }

  /**
   * 设置禁飞区
   */
  setNoFlyZones(zones: NoFlyZone[]): void {
    this.noFlyZones = zones;
  }

  // ─── 网格构建 ────────────────────────────────────

  /**
   * 创建 3D 搜索网格
   *
   * 数学原理：
   *   1. 经纬度 → 米 的近似换算（中纬度地区）：
   *      1° 纬度 ≈ 111,000m
   *      1° 经度 ≈ 100,000m（偏保守）
   *   2. gridResolution（米）决定网格密度：分辨率越小 → 网格越大 → 搜索越精确但越慢
   */
  private create3DGrid(
    start: AStarWaypoint,
    end: AStarWaypoint,
    options: AStarConfig,
  ): GridData | null {
    const gridResolution = options.gridResolution ?? this.gridResolution;

    const minLat = Math.min(start.lat, end.lat) - 0.003;
    const maxLat = Math.max(start.lat, end.lat) + 0.003;
    const minLng = Math.min(start.lng, end.lng) - 0.003;
    const maxLng = Math.max(start.lng, end.lng) + 0.003;
    const minAlt = Math.min(start.altitude, end.altitude);
    const maxAlt = Math.max(start.altitude, end.altitude) + 100;

    const latRange = maxLat - minLat;
    const lngRange = maxLng - minLng;
    const altRange = maxAlt - minAlt;

    const latMeters = latRange * 111000;
    const lngMeters = lngRange * 100000;

    const gridX = Math.ceil(lngMeters / gridResolution);
    const gridY = Math.ceil(latMeters / gridResolution);
    const gridZ = Math.ceil(altRange / gridResolution);

    const grid: GridNode[][][] = [];
    for (let x = 0; x < gridX; x++) {
      const xLayer: GridNode[][] = [];
      grid.push(xLayer);
      for (let y = 0; y < gridY; y++) {
        const yLayer: GridNode[] = [];
        xLayer.push(yLayer);
        for (let z = 0; z < gridZ; z++) {
          const lat = minLat + (y / gridY) * latRange;
          const lng = minLng + (x / gridX) * lngRange;
          const altitude = minAlt + (z / gridZ) * altRange;
          yLayer.push(new GridNode(x, y, z, lat, lng, altitude));
        }
      }
    }

    const startNode = this.getGridNode(
      grid,
      start.lat,
      start.lng,
      start.altitude,
      minLat,
      maxLat,
      minLng,
      maxLng,
      minAlt,
      maxAlt,
      gridX,
      gridY,
      gridZ,
    );
    const endNode = this.getGridNode(
      grid,
      end.lat,
      end.lng,
      end.altitude,
      minLat,
      maxLat,
      minLng,
      maxLng,
      minAlt,
      maxAlt,
      gridX,
      gridY,
      gridZ,
    );

    if (!startNode.walkable || !endNode.walkable) {
      return null;
    }

    return {
      grid,
      startNode,
      endNode,
      gridInfo: {
        minLat,
        maxLat,
        minLng,
        maxLng,
        minAlt,
        maxAlt,
        gridX,
        gridY,
        gridZ,
      },
    };
  }

  /**
   * 经纬度 → 网格坐标映射
   */
  private getGridNode(
    grid: GridNode[][][],
    lat: number,
    lng: number,
    alt: number,
    minLat: number,
    maxLat: number,
    minLng: number,
    maxLng: number,
    minAlt: number,
    maxAlt: number,
    gridX: number,
    gridY: number,
    gridZ: number,
  ): GridNode {
    const x = Math.floor(((lng - minLng) / (maxLng - minLng)) * gridX);
    const y = Math.floor(((lat - minLat) / (maxLat - minLat)) * gridY);
    const z = Math.floor(((alt - minAlt) / (maxAlt - minAlt)) * gridZ);

    const cx = Math.max(0, Math.min(gridX - 1, x));
    const cy = Math.max(0, Math.min(gridY - 1, y));
    const cz = Math.max(0, Math.min(gridZ - 1, z));

    return grid[cx]![cy]![cz]!;
  }

  // ─── 禁飞区 ──────────────────────────────────────

  /**
   * 遍历网格，将落入禁飞区的节点标记为不可通行
   */
  private markNoFlyZones(grid: GridNode[][][], gridInfo: GridInfo): void {
    if (this.noFlyZones.length === 0) return;

    let blockedCount = 0;
    for (let x = 0; x < gridInfo.gridX; x++) {
      for (let y = 0; y < gridInfo.gridY; y++) {
        for (let z = 0; z < gridInfo.gridZ; z++) {
          const node = grid[x]![y]![z]!;
          for (const zone of this.noFlyZones) {
            if (this.isPointInZone(node.lat, node.lng, node.altitude, zone)) {
              node.walkable = false;
              blockedCount++;
              break;
            }
          }
        }
      }
    }
  }

  /**
   * AABB 包围盒检测：判断一个三维点是否在禁飞区内
   */
  private isPointInZone(
    lat: number,
    lng: number,
    altitude: number,
    zone: NoFlyZone,
  ): boolean {
    return (
      lat >= zone.minLat &&
      lat <= zone.maxLat &&
      lng >= zone.minLng &&
      lng <= zone.maxLng &&
      altitude >= zone.minAlt &&
      altitude <= zone.maxAlt
    );
  }

  // ─── A* 核心 ─────────────────────────────────────

  /**
   * A* 搜索算法
   *
   * 数据结构选择：
   *   openList   → BinaryHeap（每次取 f 值最小的节点，O(log n)）
   *   closedSet  → Set<string>（已访问节点集合，O(1) 查重）
   *   key 格式   → `${x},${y},${z}` 字符串哈希
   */
  private findPathAStar(
    grid: GridNode[][][],
    startNode: GridNode,
    endNode: GridNode,
  ): GridNode[] | null {
    const openList = new BinaryHeap();
    const closedSet = new Set<string>();

    startNode.g = 0;
    startNode.h = this.heuristic(startNode, endNode);
    startNode.updateF();
    openList.enqueue(startNode);

    let iterations = 0;
    let closestNode = startNode;
    let closestDistance = startNode.h;

    while (!openList.isEmpty() && iterations < this.maxIterations) {
      iterations++;

      const currentNode = openList.dequeue()!;

      // 到达目标
      if (
        currentNode.x === endNode.x &&
        currentNode.y === endNode.y &&
        currentNode.z === endNode.z
      ) {
        return this.reconstructPath(currentNode);
      }

      // 加入闭表 — O(1)
      closedSet.add(`${currentNode.x},${currentNode.y},${currentNode.z}`);

      const distToEnd = this.heuristic(currentNode, endNode);
      if (distToEnd < closestDistance) {
        closestDistance = distToEnd;
        closestNode = currentNode;
      }

      const neighbors = this.getNeighbors(grid, currentNode);

      for (const neighbor of neighbors) {
        // 跳过不可通行或已关闭的节点
        if (
          !neighbor.walkable ||
          closedSet.has(`${neighbor.x},${neighbor.y},${neighbor.z}`)
        ) {
          continue;
        }

        const tentativeG = currentNode.g + this.distance(currentNode, neighbor);

        // neighbor.g > 0 表示曾进入过开表
        const inOpenList = neighbor.g > 0;
        if (tentativeG < neighbor.g || !inOpenList) {
          neighbor.parent = currentNode;
          neighbor.g = tentativeG;
          neighbor.h = this.heuristic(neighbor, endNode);
          neighbor.updateF();
          openList.enqueue(neighbor);
        }
      }
    }

    // 未找到完整路径 → 返回最接近目标的部分路径
    if (closestDistance < startNode.h) {
      return this.reconstructPath(closestNode);
    }

    return null;
  }

  // ─── 启发函数与距离 ──────────────────────────────

  /** 欧几里得距离启发函数（网格坐标空间） */
  private heuristic(a: GridNode, b: GridNode): number {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dz = b.z - a.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }

  /** 相邻节点间移动代价（网格单位） */
  private distance(a: GridNode, b: GridNode): number {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dz = b.z - a.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }

  /** 获取 26 方向邻居（3×3×3 - 中心 = 26） */
  private getNeighbors(grid: GridNode[][][], node: GridNode): GridNode[] {
    const neighbors: GridNode[] = [];
    const { x, y, z } = node;
    const xMax = grid.length;
    const yMax = grid[0]!.length;
    const zMax = grid[0]![0]!.length;

    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        for (let dz = -1; dz <= 1; dz++) {
          if (dx === 0 && dy === 0 && dz === 0) continue;
          const nx = x + dx;
          const ny = y + dy;
          const nz = z + dz;
          if (
            nx >= 0 &&
            nx < xMax &&
            ny >= 0 &&
            ny < yMax &&
            nz >= 0 &&
            nz < zMax
          ) {
            neighbors.push(grid[nx]![ny]![nz]!);
          }
        }
      }
    }
    return neighbors;
  }

  /** 从终点回溯到起点，重建路径 */
  private reconstructPath(endNode: GridNode): GridNode[] {
    const path: GridNode[] = [];
    let current: GridNode | null = endNode;
    while (current) {
      path.unshift(current);
      current = current.parent;
    }
    return path;
  }

  // ─── 路径平滑 ────────────────────────────────────

  /**
   * 移动平均平滑（减少锯齿航点）
   * @param waypoints  原始航点
   * @param windowSize 滑动窗口大小
   */
  private smoothPath(
    waypoints: AStarWaypoint[],
    windowSize: number = 3,
  ): AStarWaypoint[] {
    if (waypoints.length < 3) return waypoints;

    const smoothed: AStarWaypoint[] = [];

    for (let i = 0; i < waypoints.length; i++) {
      if (i === 0 || i === waypoints.length - 1) {
        smoothed.push(waypoints[i]!);
      } else {
        const start = Math.max(0, i - Math.floor(windowSize / 2));
        const end = Math.min(waypoints.length, i + Math.ceil(windowSize / 2));
        const window = waypoints.slice(start, end);

        smoothed.push({
          lat: window.reduce((sum, p) => sum + p.lat, 0) / window.length,
          lng: window.reduce((sum, p) => sum + p.lng, 0) / window.length,
          altitude:
            window.reduce((sum, p) => sum + p.altitude, 0) / window.length,
        });
      }
    }

    return smoothed;
  }

  // ─── 统计 ────────────────────────────────────────

  /**
   * 计算两个航点之间的 3D 距离（Haversine 公式 + 高度差）
   *
   * 数学原理：
   *   水平距离用 Haversine：d = 2R × arcsin(√(sin²(Δφ/2) + cos(φ₁)cos(φ₂)sin²(Δλ/2)))
   *   3D 距离 = √(水平距离² + 高度差²)
   */
  private calculate3DDistance(p1: AStarWaypoint, p2: AStarWaypoint): number {
    const R = 6371000; // 地球半径（米）
    const dLat = ((p2.lat - p1.lat) * Math.PI) / 180;
    const dLng = ((p2.lng - p1.lng) * Math.PI) / 180;
    const lat1Rad = (p1.lat * Math.PI) / 180;
    const lat2Rad = (p2.lat * Math.PI) / 180;

    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(dLng / 2) ** 2;
    const horizontalDist = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const verticalDist = Math.abs(p2.altitude - p1.altitude);

    return Math.sqrt(horizontalDist ** 2 + verticalDist ** 2);
  }

  private calculateStatistics(waypoints: AStarWaypoint[]): PathStatistics {
    let totalDistance = 0;
    let totalTime = 0;
    let maxAltitude = 0;
    let minAltitude = Infinity;
    const cruiseSpeed = 15; // m/s

    for (let i = 0; i < waypoints.length - 1; i++) {
      const segmentDist = this.calculate3DDistance(
        waypoints[i]!,
        waypoints[i + 1]!,
      );
      totalDistance += segmentDist;
      totalTime += segmentDist / cruiseSpeed;
      maxAltitude = Math.max(maxAltitude, waypoints[i]!.altitude);
      minAltitude = Math.min(minAltitude, waypoints[i]!.altitude);
    }

    return {
      totalWaypoints: waypoints.length,
      totalDistance: Math.round(totalDistance),
      totalTime: Math.round(totalTime),
      totalTimeMinutes: Math.round((totalTime / 60) * 10) / 10,
      maxAltitude: Math.round(maxAltitude),
      minAltitude: Math.round(minAltitude),
      averageSpeed: Math.round((totalDistance / totalTime) * 10) / 10,
    };
  }
}
