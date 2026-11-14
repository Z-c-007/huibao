//WebSocket 网关

import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  MessageBody,
  ConnectedSocket,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { RouteService } from './route.service';
import type { WaypointDTO } from '@uav/shared';
@WebSocketGateway({
  namespace: '/uav',
  cors: { origin: '*' },
})
export class RouteGateway {
  @WebSocketServer()
  server: Server;
  // NestJS 依赖注入：自动注入 RouteService 实例
  constructor(private readonly routeService: RouteService) {}
  /**
   * 监听前端发送的 'route:plan' 事件
   *
   * @SubscribeMessage('route:plan') 告诉 NestJS：
   *   当收到名为 'route:plan' 的消息时，调用这个方法
   *
   * @MessageBody() 提取消息体（前端 socket.emit 的第二个参数）
   * @ConnectedSocket() 获取当前连接的客户端 socket，用于单独回复
   */
  @SubscribeMessage('route:plan')
  handlePlanRoute(
    @MessageBody()
    payload: {
      waypoints: WaypointDTO[];
    },
    @ConnectedSocket()
    client: Socket,
  ): void {
    console.log(
      `[WS] 收到路径规划请求，航点数: ${payload.waypoints?.length ?? 0}`,
    );
    const result = this.routeService.calculate(payload.waypoints ?? []);
    // 将计算结果发回给请求的客户端
    // client.emit() 只发给当前客户端，server.emit() 会发给所有客户端
    client.emit('route:result', result);
  }
}
