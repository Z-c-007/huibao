import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: '/map',
      children: [
        { path: 'regulation', name: 'regulation', component: () => import('../views/RegulationView.vue'), meta: { title: '用水监管工作台' } },
        {
          path: 'map',
          name: 'map',
          component: () => import('../views/MapView.vue'),
          meta: { title: '地图一张图' },
        },
        {
          path: 'assistant',
          name: 'assistant',
          component: () => import('../views/AssistantView.vue'),
          meta: { title: 'AI 助手' },
        },
      ],
    },
  ],
})

export default router
