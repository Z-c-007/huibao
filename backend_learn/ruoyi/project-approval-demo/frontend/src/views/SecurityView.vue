<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { authApi } from '../api/auth'
import { session, signedOut } from '../stores/session'
import { useAction } from '../composables/useAction'
const sessions = ref([]),
  form = reactive({ oldPassword: '', newPassword: '', repeat: '' })
const { busy, message, run } = useAction()
const payload = computed(() => {
  try {
    const text = session.token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(text), (c) => c.charCodeAt(0))))
  } catch {
    return null
  }
})
async function load() {
  sessions.value = await authApi.sessions()
}
async function revoke(row) {
  await run(async () => {
    if (!confirm(row.current ? '确认退出当前会话？' : '确认让该会话退出登录？')) return
    await authApi.revoke(row.sessionId)
    if (row.current) signedOut('当前会话已退出')
    else await load()
  })
}
async function changePassword() {
  await run(async () => {
    if (form.newPassword !== form.repeat) throw new Error('两次新密码不一致')
    await authApi.password({ oldPassword: form.oldPassword, newPassword: form.newPassword })
    form.oldPassword = ''
    form.newPassword = ''
    form.repeat = ''
    signedOut('密码已修改，所有旧会话已失效，请重新登录')
  })
}
onMounted(() => run(load))
</script>
<template>
  <header>
    <div>
      <div class="eyebrow">ACCOUNT SECURITY</div>
      <h1>个人安全与会话</h1>
      <p>查看当前账号的登录设备，退出其他会话或修改密码。</p>
    </div>
    <button class="secondary" :disabled="busy" @click="run(load)">刷新会话</button>
  </header>
  <p v-if="message" class="notice" role="alert">{{ message }}</p>
  <section class="panel security-panel">
    <h2>在线登录会话</h2>
    <p class="muted">
      下列剩余时间从服务端 Redis 读取，显示的是最近一次刷新时的值；过期或退出后需要重新登录。
    </p>
    <article v-for="s in sessions" :key="s.sessionId" class="session-row">
      <div>
        <strong>{{ s.current ? '当前浏览器' : '其他登录会话' }}</strong
        ><span class="badge">空闲有效期剩余 {{ s.ttlSeconds }} 秒</span>
        <p>{{ s.ip }} · {{ s.issuedAt }}</p>
        <small>{{ s.userAgent }}</small
        ><code class="break-text">会话ID：{{ s.sessionId }}</code>
      </div>
      <button class="secondary danger" :disabled="busy" @click="revoke(s)">退出此会话</button>
    </article>
    <details>
      <summary>查看当前 JWT 的声明信息（学习用）</summary>
      <p>
        浏览器只做 Base64URL 解码展示；签名、过期时间和 Redis 会话是否有效，均由后端验证。jti
        对应上方会话ID。
      </p>
      <pre>{{ JSON.stringify(payload, null, 2) }}</pre>
      <p>
        服务端会话键：<code>approval:v2:session:{{ payload?.jti }}</code
        >，默认位于 Redis 第6号逻辑库。
      </p>
    </details>
  </section>
  <section class="panel security-panel">
    <h2>修改密码</h2>
    <p class="muted">
      新密码12至64位，包含字母与数字，UTF-8不超过72字节。修改后所有已登录设备需要重新登录。
    </p>
    <form class="password-form" @submit.prevent="changePassword">
      <label
        >原密码<input
          v-model="form.oldPassword"
          type="password"
          autocomplete="current-password"
          required
          maxlength="100"
          :disabled="busy" /></label
      ><label
        >新密码<input
          v-model="form.newPassword"
          type="password"
          autocomplete="new-password"
          required
          minlength="12"
          maxlength="64"
          :disabled="busy" /></label
      ><label
        >确认新密码<input
          v-model="form.repeat"
          type="password"
          autocomplete="new-password"
          required
          minlength="12"
          maxlength="64"
          :disabled="busy" /></label
      ><button :disabled="busy">修改密码并使旧会话失效</button>
    </form>
  </section>
</template>
