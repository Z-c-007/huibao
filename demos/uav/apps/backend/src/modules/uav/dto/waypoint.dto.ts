//航点 DTO（类型校验）

import { Type } from 'class-transformer';
import { IsArray, IsNumber, Min, Max, ValidateNested } from 'class-validator';
// 单个航点的校验规则
export class WaypointDTO {
  @IsNumber()
  @Min(-180)
  @Max(180)
  lng: number;

  @IsNumber()
  @Min(-90)
  @Max(90)
  lat: number;

  @IsNumber()
  @Min(0)
  @Max(10000)
  altitude: number;
}
// @Type(() => WaypointDTO)是循环引用规避写法
// 如果写成 @Type(WaypointDTO)当 WaypointDTO 类定义在后面或者存在相互引用时，运行时可能拿到 undefined。
// 箭头函数延迟求值，执行时才去取 WaypointDTO
/** 路径规划请求整体的校验规则 */
export class PlanRouteDTO {
  @IsArray() // 必须是数组
  @ValidateNested({ each: true }) // 对每个元素递归校验
  @Type(() => WaypointDTO) // 把每个元素转成 WaypointDTO 实例
  waypoints: WaypointDTO[];
}
