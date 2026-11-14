import * as Cesium from "cesium";

export function pickCartesian(
  viewer: Cesium.Viewer,
  position: Cesium.Cartesian2,
) {
  const scene = viewer.scene;
  if (scene.pickPositionSupported) {
    const cartesian = scene.pickPosition(position);
    if (Cesium.defined(cartesian)) {
      return cartesian;
    }
    const ray = scene.camera.getPickRay(position);
    if (!ray) return undefined;
    return scene.globe.pick(ray, scene);
  }
}
