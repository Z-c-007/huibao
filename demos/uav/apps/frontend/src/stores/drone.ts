import { defineStore } from "pinia";
import { mockDrones } from "@/mock";

export const useDroneStore = defineStore("drone", {
  state: () => ({
    drones: mockDrones,
    selectedDroneId: mockDrones[0]?.id ?? null,
  }),
  getters: {
    selectedDrone: (state) =>
      state.drones.find((drone) => drone.id === state.selectedDroneId) ?? null,
    onlineCount: (state) =>
      state.drones.filter((drone) => drone.status !== "offline").length,
    warningCount: (state) =>
      state.drones.filter((drone) => drone.status === "warning" || drone.riskLevel !== "low").length,
  },
  actions: {
    selectDrone(id: string) {
      this.selectedDroneId = id;
    },
  },
});
