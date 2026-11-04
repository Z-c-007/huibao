<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import LoginView from './views/LoginView.vue'
import ProjectWorkspace from './views/ProjectWorkspace.vue'
import AdminWorkspace from './views/AdminWorkspace.vue'
import SecurityView from './views/SecurityView.vue'
import { authApi } from './api/auth'
import { session, can, signedOut } from './stores/session'
const page = ref('report'),
  restoring = ref(!!session.token)
const menus = computed(() =>
  [
    { key: 'report', title: '项目信息填报', visible: can('approval:report:list') },
    { key: 'review', title: '项目信息审核', visible: can('approval:review:list') },
    {
      key: 'admin',
      title: '系统管理',
      visible: can('system:user:list') || can('system:role:list') || can('system:audit:list'),
    },
    { key: 'security', title: '个人安全与会话', visible: !!session.user },
  ].filter((m) => m.visible),
)
watch(
  () => session.user,
  (user) => {
    if (user) page.value = menus.value[0]?.key || 'security'
  },
)
async function logout() {
  try {
    await authApi.logout()
  } finally {
    signedOut('已退出登录')
  }
}
onMounted(async () => {
  if (session.token) {
    try {
      session.user = await authApi.me()
    } catch (error) {
      signedOut(error.message)
    } finally {
      restoring.value = false
    }
  }
})
</script>
<template>
  <div v-if="restoring" class="restore-screen">正在恢复登录状态…</div>
  <LoginView v-else-if="!session.user" />
  <div v-else class="workspace">
    <aside>
      <div class="brand">项目信息<span>填报与审批工作台</span></div>
      <nav>
        <button
          v-for="menu in menus"
          :key="menu.key"
          class="nav-item"
          :class="{ active: page === menu.key }"
          @click="page = menu.key"
        >
          {{ menu.title }}
        </button>
      </nav>
      <div class="aside-note">
        {{ session.user.orgName }}<br />{{ session.user.displayName
        }}<small>{{ session.user.roles.join(' / ') }}</small
        ><button class="ghost" @click="logout">退出登录</button>
      </div>
    </aside>
    <main>
      <ProjectWorkspace
        v-if="page === 'report' || page === 'review'"
        :key="page"
        :mode="page"
      /><AdminWorkspace v-else-if="page === 'admin'" /><SecurityView v-else />
    </main>
  </div>
</template>
