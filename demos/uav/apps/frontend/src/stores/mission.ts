import { defineStore } from "pinia";
import { mockMissions } from "@/mock";

export const useMissionStore = defineStore("mission", {
  state: () => ({
    missions: mockMissions,
    selectedMissionId: mockMissions[0]?.id ?? null,
  }),
  getters: {
    selectedMission: (state) =>
      state.missions.find((mission) => mission.id === state.selectedMissionId) ?? null,
    executingCount: (state) =>
      state.missions.filter((mission) => mission.status === "executing").length,
  },
  actions: {
    selectMission(id: string) {
      this.selectedMissionId = id;
    },
  },
});
