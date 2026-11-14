//路径规划核心算法   核心业务

import { Injectable } from '@nestjs/common';
interface RouteWaypoint {
  lng: number;
  lat: number;
  altitude: number;
  order: number;
}
import type { WaypointDTO } from '@uav/shared';
@Injectable()
export class RouteService {
  /**
   * 【简易版】路径规划算法
   * 当前阶段：不调用数据库，不运行复杂避障
   * 直接返回一组固定的演示航线，让前后端 WebSocket 流程先跑通
   */
  calculate(_waypoints: WaypointDTO[]): {
    success: boolean;
    waypoints: RouteWaypoint[];
    message: string;
    warnings: string[];
  } {
    // ── 固定演示航线：4个航点组成的方形飞行回路 ──
    // 这些坐标会显示在 Cesium 三维地球上
    const demoWaypoints: RouteWaypoint[] = [
      { lng: -74.006, lat: 40.7128, altitude: 120, order: 1 },
      { lng: -73.995, lat: 40.7128, altitude: 160, order: 2 },
      { lng: -73.995, lat: 40.7228, altitude: 120, order: 3 },
      { lng: -74.016, lat: 40.7228, altitude: 160, order: 4 },
      { lng: -74.006, lat: 40.7128, altitude: 120, order: 5 }, // 回到起点
    ];

    return {
      success: true,
      waypoints: demoWaypoints,
      message: `航线规划完成：共 ${demoWaypoints.length} 个航点`,
      warnings: ['当前为简易测试模式，未执行实际避障计算'],
    };
  }
}
