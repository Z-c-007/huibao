// 职责：WebSocket 实时广播层
// 架构位置：NestJS Gateway 层（跨模块共享 /uav 命名空间）
// 关键设计：Gateway 不持有数据，只暴露广播方法给 Controller 调用
// 与 RouteGateway 共用 /uav 命名空间，客户端只需连接一个 socket
import { WebSocketGateway, WebSocketServer } from '@nestjs/websockets';
import { Server } from 'socket.io';
import type { FenceEntity } from '@uav/shared';

/**
 * 围栏变更实时同步网关
 *
 * 与 RouteGateway 共用 `/uav` 命名空间：
 * - RouteGateway 处理 `route:plan` → `route:result`
 * - AirspaceGateway 广播 `fence:created` / `fence:updated` / `fence:deleted`
 *
 * 前端只需连接一个 socket (`ws://localhost:3000/uav`)
 * 即可同时接收路径规划结果和围栏变更通知。
 */
@WebSocketGateway({
  namespace: '/uav',
  cors: { origin: '*' },
})
export class AirspaceGateway {
  @WebSocketServer()
  server: Server;

  /**
   * 广播：围栏被创建
   * 所有已连接客户端都会收到新围栏的完整数据
   */
  broadcastFenceCreated(fence: FenceEntity): void {
    this.server.emit('fence:created', fence);
  }

  /**
   * 广播：围栏被更新
   */
  broadcastFenceUpdated(fence: FenceEntity): void {
    this.server.emit('fence:updated', fence);
  }

  /**
   * 广播：围栏被删除
   * 只发送 id，减少网络传输量
   */
  broadcastFenceDeleted(fenceId: string): void {
    this.server.emit('fence:deleted', { id: fenceId });
  }
}
