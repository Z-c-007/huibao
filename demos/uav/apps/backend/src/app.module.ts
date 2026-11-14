import { Module } from '@nestjs/common';
import { UavModule } from './modules/uav/uav.module';
import { AirspaceModule } from './modules/AirspaceModule/airspace.module';
@Module({
  imports: [UavModule, AirspaceModule],
})
export class AppModule {}
