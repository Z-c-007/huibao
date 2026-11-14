import { defineStore } from "pinia";

const defaultLayers = [
  { key: "terrain", label: "地形", enabled: true },
  { key: "tileset", label: "城市模型", enabled: true },
  { key: "routes", label: "航线", enabled: true },
  { key: "drones", label: "无人机", enabled: true },
  { key: "alerts", label: "风险高亮", enabled: true },
];

export const useMapStore = defineStore("map", {
  state: () => ({
    activeTool: "browse",
    layers: defaultLayers,
  }),
  getters: {
    enabledLayerCount: (state) => state.layers.filter((layer) => layer.enabled).length,
  },
  actions: {
    setActiveTool(tool: string) {
      this.activeTool = tool;
    },
    toggleLayer(key: string) {
      const layer = this.layers.find((item) => item.key === key);
      if (layer) {
        layer.enabled = !layer.enabled;
      }
    },
  },
});
