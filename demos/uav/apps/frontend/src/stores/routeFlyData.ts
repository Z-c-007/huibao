import { defineStore } from "pinia";
import { computed, ref } from "vue";

export interface FlightRoute {
  id: string;
  name: string;
  waypoints: RouteFlyWaypoint[];
  createdAt: number;
  color?: string;
}
export interface RouteFlyWaypoint {
  lng: number;
  lat: number;
  altitude: number;
  order: number;
}
export const useRouteFlyDataStore = defineStore("RouteFlyData", () => {
  const routes = ref<FlightRoute[]>([]);
  const activeRouteId = ref<string | null>(null);
  const activeRoute = computed<FlightRoute | null>(
    () => routes.value.find((r) => r.id === activeRouteId.value) ?? null,
  );
  const activeWaypoints = computed<RouteFlyWaypoint[]>(
    () => activeRoute.value?.waypoints ?? [],
  );

  const routeCount = computed(() => routes.value.length);
  /**
   * 添加路由
   * @param route 路由
   */
  const addRoute = (route: FlightRoute) => {
    routes.value.push(route);
    activeRouteId.value = route.id;
  };
  /**
   * 删除路由
   * @param id 路由id
   */
  const removeRoute = (id: string) => {
    routes.value = routes.value.filter((r) => r.id !== id);
    if (activeRouteId.value === id) {
      activeRouteId.value = routes.value.at(-1)?.id ?? null;
    }
  };
  /**
   * 设置当前路由
   * @param id 路由id
   */
  const setActiveRoute = (id: string | null) => {
    activeRouteId.value = id;
  };
  /**
   * 清除所有路由
   */
  const clearAllRoutes = () => {
    routes.value = [];
    activeRouteId.value = null;
  };
  return {
    routes,
    activeRouteId,
    activeRoute,
    activeWaypoints,
    routeCount,
    addRoute,
    removeRoute,
    setActiveRoute,
    clearAllRoutes,
  };
});
