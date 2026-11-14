export type AlertLevel = "info" | "warning" | "critical";

export type AlertStatus = "unread" | "processing" | "closed";

export interface AlertItem {
  id: string;
  type: string;
  level: AlertLevel;
  title: string;
  content: string;
  targetId: string;
  targetType: "drone" | "mission" | "zone" | "system";
  status: AlertStatus;
  time: string;
}
