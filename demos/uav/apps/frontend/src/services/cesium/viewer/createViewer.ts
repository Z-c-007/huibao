import * as Cesium from "cesium";
import { defaultViewerOptions } from "./viewerOptions.ts";
import type { CreateViewerOptions } from "./types.ts";
export function createViewer(
  container: string | HTMLElement,
  options: CreateViewerOptions = {},
): Cesium.Viewer {
  const { accessToken, viewerOptions } = options;

  if (accessToken) {
    Cesium.Ion.defaultAccessToken = accessToken;
  }
  const mergedOptions: Cesium.Viewer.ConstructorOptions = {
    ...defaultViewerOptions,
    ...viewerOptions,
  };
  const viewer = new Cesium.Viewer(container, mergedOptions);

  // 隐藏版权信息
  const creditContainer = viewer.cesiumWidget
    .creditContainer as HTMLElement | null;
  if (creditContainer) {
    creditContainer.style.display = "none";
  }
  return viewer;
}
