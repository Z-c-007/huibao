import { createRouter, createWebHistory } from "vue-router";
import OverviewPage from "@/views/overview/OverviewPage.vue";
import MapView from "@/views/MapView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "overview",
      component: OverviewPage,
    },
    {
      path: "/map",
      name: "map",
      component: MapView,
    },
  ],
});

export default router;
