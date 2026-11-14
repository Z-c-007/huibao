import { defineStore } from "pinia";
import { mockAlerts } from "@/mock";

export const useAlertStore = defineStore("alert", {
  state: () => ({
    alerts: mockAlerts,
    highlightedAlertId: mockAlerts[0]?.id ?? null,
  }),
  getters: {
    unreadCount: (state) => state.alerts.filter((alert) => alert.status === "unread").length,
    criticalCount: (state) => state.alerts.filter((alert) => alert.level === "critical").length,
  },
  actions: {
    highlightAlert(id: string) {
      this.highlightedAlertId = id;
    },
    markAsRead(id: string) {
      const alert = this.alerts.find((item) => item.id === id);
      if (alert && alert.status === "unread") {
        alert.status = "processing";
      }
    },
  },
});
