// 职责：核心业务层，唯一数据持有者
// 架构位置：NestJS Service 层
// 未来演进：内存 Map → TypeORM Repository<FenceEntity>
import { Injectable, NotFoundException } from '@nestjs/common';
import { generateUniqueID } from '@uav/shared';
import type {
  FenceEntity,
  CreateFenceRequest,
  UpdateFenceRequest,
} from '@uav/shared';

@Injectable()
export class AirspaceService {
  /**
   * 内存存储 — 未来替换为 TypeORM Repository
   * key: fenceId  →  value: FenceEntity
   *
   * 使用 Map 而非数组是为了 O(1) 按 ID 查找，
   * 与未来 PostGIS 的主键索引行为保持一致。
   */
  private readonly fences: Map<string, FenceEntity> = new Map();
  /**
   * 查询所有围栏
   * 对应 SQL: SELECT * FROM fences
   */
  findAll(): FenceEntity[] {
    return Array.from(this.fences.values());
  }
  /**
   * 按 ID 查询单个围栏
   * 对应 SQL: SELECT * FROM fences WHERE id = $1
   *
   * 未找到时抛出 NotFoundException，
   * NestJS 会自动将其转换为 404 响应。
   */
  findById(id: string): FenceEntity {
    const fence = this.fences.get(id);
    if (!fence) {
      throw new NotFoundException(`围栏 ${id} 不存在`);
    }
    return fence;
  } /**
   * 创建围栏
   * 对应 SQL: INSERT INTO fences (...) VALUES (...) RETURNING *
   */
  create(dto: CreateFenceRequest): FenceEntity {
    const now = new Date().toISOString();

    const entity: FenceEntity = {
      id: generateUniqueID(),
      name: dto.name,
      type: dto.type,
      riskLevel: dto.riskLevel,
      // 浅拷贝坐标数组，防止外部意外修改
      coordinates: dto.coordinates.map((v) => ({ ...v })),
      minAltitude: dto.minAltitude,
      maxAltitude: dto.maxAltitude,
      activeTime: dto.activeTime ?? '永久',
      remark: dto.remark,
      createdAt: now,
      updatedAt: now,
    };

    this.fences.set(entity.id, entity);
    return entity;
  } /**
   * 部分更新围栏（PATCH 语义）
   * 对应 SQL: UPDATE fences SET ... WHERE id = $1 RETURNING *
   *
   * 防御性设计：
   * 1. 先查是否存在，不存在直接抛 404
   * 2. id 和 createdAt 不可变
   * 3. 使用展开运算符合并，只覆盖传入的字段
   */
  update(id: string, dto: UpdateFenceRequest): FenceEntity {
    const existing = this.findById(id);

    // 如果更新了坐标，同样做浅拷贝防止外部修改
    const coordinates =
      dto.coordinates?.map((v) => ({ ...v })) ?? existing.coordinates;

    const updated: FenceEntity = {
      ...existing,
      ...dto,
      coordinates,
      id: existing.id,
      createdAt: existing.createdAt,
      updatedAt: new Date().toISOString(),
    };

    this.fences.set(id, updated);
    return updated;
  }

  /**
   * 删除围栏
   * 对应 SQL: DELETE FROM fences WHERE id = $1
   *
   * 删除不存在 ID 时同样抛 404，与 REST 语义保持一致。
   */
  delete(id: string): void {
    if (!this.fences.has(id)) {
      throw new NotFoundException(`围栏 ${id} 不存在`);
    }
    this.fences.delete(id);
  }
}
