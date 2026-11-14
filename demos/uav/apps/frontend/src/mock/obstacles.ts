import type { ObstacleZone } from "@/types";

export const mockObstacles: ObstacleZone[] = [
  {
    id: "zone-01",
    name: "国贸核心限飞区",
    type: "no-fly-zone",
    riskLevel: "high",
    minAltitude: 0,
    maxAltitude: 300,
    activeTime: "长期",
    center: { lng: 116.403, lat: 39.908, altitude: 0 },
    remark: "政府敏感区域，禁止任务穿越。",
  },
  {
    id: "zone-02",
    name: "东三环临时施工吊塔",
    type: "temporary",
    riskLevel: "medium",
    minAltitude: 60,
    maxAltitude: 180,
    activeTime: "2026-04-29 20:00 - 2026-04-30 06:00",
    center: { lng: 116.399, lat: 39.905, altitude: 0 },
    remark: "夜间施工，注意动态避障。",
  },
  {
    id: "zone-03",
    name: "物流园低空走廊",
    type: "limit-zone",
    riskLevel: "low",
    minAltitude: 80,
    maxAltitude: 150,
    activeTime: "工作日 08:00 - 22:00",
    center: { lng: 116.394, lat: 39.902, altitude: 0 },
    remark: "建议使用标准航路。",
  },
];
