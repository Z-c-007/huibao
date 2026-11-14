//模块注册

import { Module } from '@nestjs/common';

import { RouteGateway } from './route/route.gateway';
import { RouteService } from './route/route.service';
@Module({
  providers: [RouteGateway, RouteService],
})
export class UavModule {}
