import type * as Cesium from "cesium";

export interface AddTilesetOptions {
  assetId: number;
}

export interface AddDroneModelOptions {
  url: string;
  longitude: number;
  latitude: number;
  height: number;
  scale?: number;
  minimumPixelSize?: number;
  allowPicking?: boolean;
  asynchronous?: boolean;
}

export interface DroneModelResult {
  model: Cesium.Model;
  position: Cesium.Cartesian3;
  modelMatrix: Cesium.Matrix4;
}
