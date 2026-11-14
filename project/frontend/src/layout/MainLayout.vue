<script setup lang="ts">
import { useRoute } from 'vue-router'
import { MapLocation, ChatDotRound, Lock, User, DataAnalysis } from '@element-plus/icons-vue'

const route = useRoute()
</script>

<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo"><span class="logo-mark">水</span>用水预算监管平台</div>
      <el-menu
        :default-active="route.path"
        router
        background-color="#102238"
        text-color="#bfcbd9"
        active-text-color="#8ea5ff"
      >
        <el-menu-item index="/regulation"><el-icon><DataAnalysis /></el-icon><span>监管工作台</span></el-menu-item>
        <el-menu-item index="/map">
          <el-icon><MapLocation /></el-icon>
          <span>地图一张图</span>
        </el-menu-item>
        <el-menu-item index="/assistant">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-menu-item>
        <!-- 克制铁律：只留占位，绝不实现 -->
        <el-menu-item index="/data" disabled>
          <el-icon><Lock /></el-icon>
          <span>数据管理</span>
        </el-menu-item>
        <el-menu-item index="/user" disabled>
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="header-title">{{ route.meta.title }}</span>
        <span class="header-sub">用水预算监管 · 智能分析</span>
      </el-header>
      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background-color: #102238;
  border-right: 1px solid #1d3048;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  gap: 9px;
  font-size: 13px;
  font-weight: 600;
}
.logo-mark { display:grid; place-items:center; width:25px; height:28px; border-radius:8px; color:#c9d6ff; background:#253b5b; font-size:15px; }
.el-menu :deep(.el-menu-item) { height:45px; line-height:45px; margin:7px 10px; border-radius:9px; padding-left:16px !important; font-size:12px; }
.el-menu :deep(.el-menu-item.is-active) { background:#213858; }
.el-menu :deep(.el-menu-item:not(.is-disabled):hover) { background:#1a304c; }
.el-menu {
  border-right: none;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #edf0f5;
  background: #fff;
}
.header-title {
  font-size: 15px;
  color: #30445f;
  font-weight: 600;
}
.header-sub {
  font-size: 12px;
  color: #909399;
}
.main {
  padding: 0;
  position: relative; /* MapView 的 Cesium 容器以此为定位基准 */
  overflow: hidden;
}
</style>
