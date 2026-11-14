import { defineStore } from "pinia";

export type WorkspaceMode = "overview" | "planning" | "monitoring";

export const useAppStore = defineStore("app", {
  state: () => ({
    mode: "overview" as WorkspaceMode,
    systemName: "无人机三维航线调度与避障系统",
    environmentLabel: "Mock Sandbox",
  }),
  actions: {
    setMode(mode: WorkspaceMode) {
      this.mode = mode;
    },
  },
});
