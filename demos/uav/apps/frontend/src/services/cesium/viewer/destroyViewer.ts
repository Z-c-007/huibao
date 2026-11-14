import * as Cesium from "cesium";

export function destroyViewer(viewer: Cesium.Viewer | null | undefined): null {
  if (viewer && !viewer.isDestroyed()) {
    viewer.destroy();
  }
  return null;
}
