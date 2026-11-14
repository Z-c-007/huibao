import { defineStore } from "pinia";
import { mockObstacles } from "@/mock";

export const useObstacleStore = defineStore("obstacle", {
  state: () => ({
    zones: mockObstacles,
    selectedZoneId: mockObstacles[0]?.id ?? null,
  }),
  getters: {
    selectedZone: (state) =>
      state.zones.find((zone) => zone.id === state.selectedZoneId) ?? null,
    highRiskCount: (state) => state.zones.filter((zone) => zone.riskLevel === "high").length,
  },
  actions: {
    selectZone(id: string) {
      this.selectedZoneId = id;
    },
  },
});
