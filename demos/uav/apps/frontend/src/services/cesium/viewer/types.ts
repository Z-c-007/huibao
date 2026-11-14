import * as Cesium from "cesium";

export type ViewerContainer = HTMLElement;

export interface CreateViewerOptions {
  accessToken?: string;
  viewerOptions?:
    | Cesium.Viewer.ConstructorOptions
    | Cesium.TerrainProvider
    | Cesium.EllipsoidTerrainProvider;
}
