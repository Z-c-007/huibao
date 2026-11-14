import { Module } from '@nestjs/common';
import { AirspaceController } from './airspace.controller';
import { AirspaceService } from './airspace.service';
import { AirspaceGateway } from './airspace.gateway';

@Module({
  controllers: [AirspaceController],
  providers: [AirspaceService, AirspaceGateway],
  exports: [AirspaceService],
})
export class AirspaceModule {}
