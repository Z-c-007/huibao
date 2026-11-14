import * as Cesium from "cesium";
import type { AddTilesetOptions } from "./types.ts";

export async function addTileset(
  viewer: Cesium.Viewer,
  options: AddTilesetOptions,
): Promise<Cesium.Cesium3DTileset> {
  const { assetId } = options;

  const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(assetId);

  viewer.scene.primitives.add(tileset);

  return tileset;
}
