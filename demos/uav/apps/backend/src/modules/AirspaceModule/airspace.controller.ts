// 职责：HTTP 控制层，只做协议转换
// 架构位置：NestJS Controller 层
// 关键设计：控制器不写任何业务逻辑，全部委托给 Service
//  注入 Gateway 以在 CRUD 成功后广播实时事件
import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  HttpCode,
  HttpStatus,
  Inject,
  forwardRef,
} from '@nestjs/common';
import { AirspaceGateway } from './airspace.gateway';
import { AirspaceService } from './airspace.service';
import { CreateFenceDTO, UpdateFenceDTO } from './dto/fence.dto';
@Controller('api/airspace')
export class AirspaceController {
  constructor(
    @Inject(forwardRef(() => AirspaceService))
    private readonly airspaceService: AirspaceService,
    @Inject(forwardRef(() => AirspaceGateway))
    private readonly airspaceGateway: AirspaceGateway,
  ) {}
  /**
   * GET /api/airspace
   * 获取全部围栏列表
   */
  @Get()
  findAll() {
    const data = this.airspaceService.findAll();
    return {
      success: true,
      data,
      total: data.length,
    };
  }
  /**
   * GET /api/airspace/:id
   * 获取单个围栏详情
   */
  @Get(':id')
  findById(@Param('id') id: string) {
    return {
      success: true,
      data: this.airspaceService.findById(id),
    };
  }
  /**
   * POST /api/airspace
   * 创建新围栏
   *
   * ValidationPipe 会在进入方法前：
   * 1. 校验 Body 是否匹配 CreateFenceDTO 装饰器规则
   * 2. transform:true 将普通对象转换为 CreateFenceDTO 实例
   */
  @Post()
  @HttpCode(HttpStatus.CREATED)
  create(@Body() dto: CreateFenceDTO) {
    const fence = this.airspaceService.create(dto);

    // 创建成功后广播给所有 WebSocket 客户端
    this.airspaceGateway.broadcastFenceCreated(fence);

    return {
      success: true,
      data: fence,
      message: `围栏 "${fence.name}" 创建成功`,
    };
  }

  /**
   * PATCH /api/airspace/:id
   * 部分更新围栏属性
   */
  @Patch(':id')
  update(@Param('id') id: string, @Body() dto: UpdateFenceDTO) {
    const fence = this.airspaceService.update(id, dto);
    this.airspaceGateway.broadcastFenceUpdated(fence);
    return {
      success: true,
      data: fence,
      message: `围栏 "${fence.name}" 更新成功`,
    };
  }

  /**
   * DELETE /api/airspace/:id
   * 删除围栏
   *
   * 204 No Content：删除成功后无响应体，
   * 只通过 WebSocket 广播删除事件。
   */
  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  delete(@Param('id') id: string): void {
    this.airspaceService.delete(id);
    this.airspaceGateway.broadcastFenceDeleted(id);
  }
}
