<script setup>
import { reactive } from 'vue'
import { authApi } from '../api/auth'
import { session, signedIn } from '../stores/session'
import { useAction } from '../composables/useAction'
const form = reactive({ username: 'report_b', password: '' })
const { busy, message, run } = useAction()
async function login() {
  await run(async () => {
    const data = await authApi.login(form)
    signedIn(data.token, data.user)
    form.password = ''
  })
}
</script>
<template>
  <div class="login-shell">
    <section class="intro">
      <div class="eyebrow">PROJECT WORKSPACE</div>
      <h1>每一份填报，<br />都有清晰的去向。</h1>
      <p>组织分级 · 多人或签 · 审批留痕</p>
      <div class="route-preview">三级公司 <span>→</span> 二级公司 <span>→</span> 集团</div>
    </section>
    <form class="login-card" @submit.prevent="login">
      <h2>登录业务工作台</h2>
      <p>使用已分配业务权限的账号登录。</p>
      <p v-if="session.notice" class="notice">{{ session.notice }}</p>
      <label
        >账号<input
          v-model="form.username"
          required
          maxlength="50"
          autocomplete="username"
          :disabled="busy"
      /></label>
      <label
        >密码<input
          v-model="form.password"
          required
          type="password"
          maxlength="100"
          autocomplete="current-password"
          :disabled="busy"
      /></label>
      <button :disabled="busy">{{ busy ? '正在登录…' : '进入工作台 →' }}</button>
      <p class="error" role="alert">{{ message }}</p>
      <small>连续登录失败会暂时锁定；账号与权限由系统管理员维护。</small>
    </form>
  </div>
</template>
