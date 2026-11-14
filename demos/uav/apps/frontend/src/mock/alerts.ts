import type { AlertItem } from "@/types";

export const mockAlerts: AlertItem[] = [
  {
    id: "alert-01",
    type: "battery-low",
    level: "warning",
    title: "物流二号电量低于阈值",
    content: "当前电量 31%，建议优先执行返航或降级任务。",
    targetId: "drone-02",
    targetType: "drone",
    status: "unread",
    time: "2026-04-29 22:07:58",
  },
  {
    id: "alert-02",
    type: "zone-conflict",
    level: "critical",
    title: "航线与临时施工吊塔风险区重叠",
    content: "园区物流投送任务需重新规划中段航线高度。",
    targetId: "mission-02",
    targetType: "mission",
    status: "processing",
    time: "2026-04-29 22:06:41",
  },
  {
    id: "alert-03",
    type: "device-offline",
    level: "info",
    title: "应急四号离线",
    content: "设备已超过 10 分钟未上报遥测数据。",
    targetId: "drone-04",
    targetType: "drone",
    status: "unread",
    time: "2026-04-29 21:59:03",
  },
];
