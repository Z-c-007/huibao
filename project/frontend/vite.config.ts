import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vitePluginCesium from 'vite-plugin-cesium'

// vite-plugin-cesium：自动拷贝 Cesium 静态资源（Workers/Assets/Widgets）
// 并注入 window.CESIUM_BASE_URL——没有它 Cesium 在 Vite 下起不来
export default defineConfig({
  plugins: [vue(), vitePluginCesium()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      // 前端用相对路径 /api/*，由 Vite 转发到 FastAPI（绕开 CORS，生产换 Nginx）
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
