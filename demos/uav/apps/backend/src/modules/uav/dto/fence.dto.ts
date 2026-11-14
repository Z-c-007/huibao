// 围栏 DTO
import {
  IsNumber,
  Max,
  Min,
  IsString,
  IsEnum,
  IsArray,
  ArrayMinSize,
  ValidateNested,
  IsOptional,
} from 'class-validator';
import { Type } from 'class-transformer';
/** 单个顶点的校验规则 */
export class FenceVertexDTO {
  @IsNumber()
  @Min(-180)
  @Max(180)
  lng: number; // 经度

  @IsNumber()
  @Min(-90)
  @Max(90)
  lat: number; // 纬度

  @IsNumber()
  @Min(0)
  @Max(10000)
  altitude: number; // 海拔高度(米)
}
/** 创建围栏的校验规则 */
export class CreateFenceDTO {
  @IsString()
  name: string;

  @IsEnum(['no-fly-zone', 'limit-zone', 'temporary'] as const)
  type: 'no-fly-zone' | 'limit-zone' | 'temporary';

  @IsEnum(['low', 'medium', 'high'] as const)
  riskLevel: 'low' | 'medium' | 'high';

  @IsArray()
  @ArrayMinSize(3)
  @ValidateNested({ each: true })
  @Type(() => FenceVertexDTO)
  coordinates: FenceVertexDTO[];

  @IsNumber()
  @Min(0)
  minAltitude: number;

  @IsNumber()
  @Min(0)
  @Max(10000)
  maxAltitude: number;

  @IsOptional()
  @IsString()
  activeTime?: string;

  @IsOptional()
  @IsString()
  remark?: string;
}
/** 更新围栏的校验规则（全部可选） */
export class UpdateFenceDTO {
  @IsOptional()
  @IsString()
  name?: string;

  @IsOptional()
  @IsEnum(['no-fly-zone', 'limit-zone', 'temporary'] as const)
  type?: 'no-fly-zone' | 'limit-zone' | 'temporary';

  @IsOptional()
  @IsEnum(['low', 'medium', 'high'] as const)
  riskLevel?: 'low' | 'medium' | 'high';

  @IsOptional()
  @IsArray()
  @ArrayMinSize(3)
  @ValidateNested({ each: true })
  @Type(() => FenceVertexDTO)
  coordinates?: FenceVertexDTO[];

  @IsOptional()
  @IsNumber()
  @Min(0)
  minAltitude?: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @Max(10000)
  maxAltitude?: number;

  @IsOptional()
  @IsString()
  activeTime?: string;

  @IsOptional()
  @IsString()
  remark?: string;
}
