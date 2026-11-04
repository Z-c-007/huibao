<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { adminApi } from '../api/admin'
import { session, can } from '../stores/session'
import { useAction } from '../composables/useAction'
const tabs = computed(() =>
  [
    { id: 'users', name: '用户与角色分配', allowed: can('system:user:list') },
    { id: 'roles', name: '角色功能权限', allowed: can('system:role:list') },
    { id: 'logs', name: '登录与操作日志', allowed: can('system:audit:list') },
  ].filter((t) => t.allowed),
)
const tab = ref(tabs.value[0]?.id),
  rows = ref([]),
  total = ref(0),
  page = ref(1),
  category = ref('')
const roles = ref([]),
  permissions = ref([]),
  organizations = ref([]),
  roleEditor = ref(null),
  userRoleEditor = ref(null),
  creating = ref(false)
const newUser = reactive({ username: '', displayName: '', orgId: null, password: '', roleIds: [] })
const { busy, message, run } = useAction()
function changePage(offset = 0) {
  page.value = offset === 0 ? 1 : page.value + offset
  return run(load)
}
const groups = ['REPORT', 'REVIEW', 'ADMIN'],
  groupNames = { REPORT: '材料填报', REVIEW: '材料审核', ADMIN: '系统管理' }
async function metadata() {
  if (can('system:role:list')) {
    roles.value = await adminApi.roles()
    permissions.value = await adminApi.permissions()
  }
  if (can('system:user:list') || can('system:user:create'))
    organizations.value = await adminApi.organizations()
}
async function load() {
  if (tab.value === 'users') {
    const data = await adminApi.users(page.value)
    rows.value = data.rows
    total.value = data.total
  } else if (tab.value === 'logs') {
    const data = await adminApi.logs(page.value, category.value)
    rows.value = data.rows
    total.value = data.total
  } else {
    roles.value = await adminApi.roles()
    rows.value = []
    total.value = 0
  }
}
async function switchTab(id) {
  tab.value = id
  page.value = 1
  await run(load)
}
function roleNames(ids) {
  return ids.map((id) => roles.value.find((r) => r.role.id === id)?.role.name || id).join('、')
}
function startCreate() {
  if (!can('system:user:assign')) {
    message.value = '新增带角色的账号还需要角色分配权限'
    return
  }
  Object.assign(newUser, {
    username: '',
    displayName: '',
    orgId: organizations.value[0]?.id,
    password: '',
    roleIds: [],
  })
  creating.value = true
}
async function createUser() {
  await run(async () => {
    await adminApi.createUser(newUser)
    newUser.password = ''
    creating.value = false
    await load()
    message.value = '用户已创建'
  })
}
async function assignRoles() {
  await run(async () => {
    await adminApi.assign(userRoleEditor.value.id, userRoleEditor.value.roleIds)
    userRoleEditor.value = null
    await load()
    message.value = '角色已更新，该用户的旧登录会话已失效'
  })
}
async function toggle(row) {
  await run(async () => {
    if (!confirm(`确认${row.user.enabled ? '停用' : '启用'}该用户？旧会话将失效。`)) return
    await adminApi.enabled(row.user.id, !row.user.enabled)
    await load()
  })
}
async function revoke(row) {
  await run(async () => {
    if (!confirm('确认让该用户所有登录会话失效？')) return
    await adminApi.revoke(row.user.id)
    message.value = '该用户所有旧凭证已失效'
  })
}
async function savePermissions() {
  await run(async () => {
    await adminApi.rolePermissions(roleEditor.value.role.id, roleEditor.value.permissions)
    roleEditor.value = null
    await load()
    message.value = '权限已更新，持有该角色的用户需要重新登录'
  })
}
onMounted(() =>
  run(async () => {
    await metadata()
    await load()
  }),
)
</script>
<template>
  <header>
    <div>
      <div class="eyebrow">SYSTEM ADMINISTRATION</div>
      <h1>系统管理</h1>
      <p>角色与功能权限由数据库配置，修改后旧会话失效。</p>
    </div>
    <button
      v-if="tab === 'users' && can('system:user:create')"
      :disabled="busy"
      @click="startCreate"
    >
      ＋ 新增用户
    </button>
  </header>
  <div class="section-tabs">
    <button
      v-for="item in tabs"
      :key="item.id"
      :class="tab === item.id ? '' : 'secondary'"
      :disabled="busy"
      @click="switchTab(item.id)"
    >
      {{ item.name }}
    </button>
  </div>
  <p v-if="message" class="notice" role="alert">{{ message }}</p>
  <section v-if="tab === 'users'" class="panel">
    <div class="toolbar">
      <button class="secondary" :disabled="busy" @click="run(load)">刷新用户</button
      ><span class="muted">共 {{ total }} 个用户</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>账号 / 姓名</th>
            <th>单位</th>
            <th>角色</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.user.id">
            <td>
              <strong>{{ row.user.username }}</strong
              ><small>{{ row.user.displayName }}</small>
            </td>
            <td>{{ row.user.orgName }}</td>
            <td>{{ roleNames(row.roleIds) }}</td>
            <td>
              <span class="badge">{{ row.user.enabled ? '启用' : '停用' }}</span>
            </td>
            <td>
              <template v-if="row.user.id !== session.user.id && row.user.username !== 'admin'"
                ><button
                  v-if="can('system:user:assign')"
                  class="link"
                  :disabled="busy"
                  @click="
                    userRoleEditor = {
                      id: row.user.id,
                      username: row.user.username,
                      roleIds: [...row.roleIds],
                    }
                  "
                >
                  分配角色</button
                ><button
                  v-if="can('system:user:disable')"
                  class="link"
                  :disabled="busy"
                  @click="toggle(row)"
                >
                  {{ row.user.enabled ? '停用' : '启用' }}
                </button></template
              ><button
                v-if="can('system:user:revoke')"
                class="link danger"
                :disabled="busy"
                @click="revoke(row)"
              >
                使会话失效
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer>
      <button
        class="secondary"
        :disabled="busy || page === 1"
        @click="changePage(-1)"
      >
        上一页</button
      ><span>第 {{ page }} 页</span
      ><button
        class="secondary"
        :disabled="busy || page * 10 >= total"
        @click="changePage(1)"
      >
        下一页
      </button>
    </footer>
  </section>
  <section v-else-if="tab === 'roles'" class="role-grid">
    <article v-for="entry in roles" :key="entry.role.id" class="panel role-card">
      <span class="badge">{{ entry.role.code }}</span>
      <h2>{{ entry.role.name }}</h2>
      <p class="muted">
        {{ entry.permissions.length }} 项功能权限 {{ entry.role.builtIn ? '· 内置管理角色' : '' }}
      </p>
      <ul>
        <li v-for="code in entry.permissions" :key="code">
          {{ permissions.find((p) => p.code === code)?.name || code }}
        </li>
      </ul>
      <button
        v-if="can('system:role:edit') && !entry.role.builtIn"
        class="secondary"
        :disabled="busy"
        @click="roleEditor = { role: { ...entry.role }, permissions: [...entry.permissions] }"
      >
        配置功能权限
      </button>
    </article>
  </section>
  <section v-else class="panel">
    <div class="toolbar">
      <label
        >日志类型<select
          v-model="category"
          :disabled="busy"
          @change="changePage()"
        >
          <option value="">全部</option>
          <option value="AUTH">登录与账号安全</option>
          <option value="BUSINESS">业务操作</option>
          <option value="ADMIN">系统管理</option>
        </select></label
      ><button class="secondary" :disabled="busy" @click="run(load)">刷新日志</button
      ><span class="muted">共 {{ total }} 条</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间 / 操作</th>
            <th>账号</th>
            <th>结果</th>
            <th>请求ID / 耗时</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>
              {{ row.createdAt?.replace('T', ' ') }}<small>{{ row.operation }}</small>
            </td>
            <td>
              {{ row.actorName || '未登录' }}<small>{{ row.ip }}</small>
            </td>
            <td>
              <span class="badge" :class="row.success ? 'APPROVED' : 'REJECTED'">{{
                row.httpStatus
              }}</span
              ><small>{{ row.message }}</small>
            </td>
            <td>
              <code class="break-text">{{ row.requestId }}</code
              ><small>{{ row.durationMillis }} ms · {{ row.httpMethod }} {{ row.path }}</small>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="4" class="empty">暂无日志。</td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer>
      <button
        class="secondary"
        :disabled="busy || page === 1"
        @click="changePage(-1)"
      >
        上一页</button
      ><span>第 {{ page }} 页</span
      ><button
        class="secondary"
        :disabled="busy || page * 10 >= total"
        @click="changePage(1)"
      >
        下一页
      </button>
    </footer>
  </section>
  <div v-if="creating" class="overlay">
    <form class="modal" @submit.prevent="createUser">
      <div class="modal-head">
        <h2>新增用户</h2>
        <button class="ghost" type="button" :disabled="busy" @click="creating = false">关闭</button>
      </div>
      <div class="grid">
        <label
          >账号<input
            v-model="newUser.username"
            required
            pattern="[A-Za-z0-9_]{3,30}"
            autocomplete="off" /></label
        ><label>姓名<input v-model="newUser.displayName" required maxlength="50" /></label
        ><label
          >单位<select v-model="newUser.orgId" required>
            <option v-for="org in organizations" :key="org.id" :value="org.id">
              {{ org.name }}
            </option>
          </select></label
        ><label
          >初始密码<input
            v-model="newUser.password"
            type="password"
            required
            minlength="12"
            maxlength="64"
            autocomplete="new-password"
        /></label>
      </div>
      <fieldset>
        <legend>至少选择一个角色</legend>
        <label v-for="entry in roles" :key="entry.role.id" class="check"
          ><input v-model="newUser.roleIds" type="checkbox" :value="entry.role.id" />{{
            entry.role.name
          }}</label
        >
      </fieldset>
      <p class="error">{{ message }}</p>
      <div class="actions">
        <button :disabled="busy || !newUser.roleIds.length">创建用户</button>
      </div>
    </form>
  </div>
  <div v-if="userRoleEditor" class="overlay">
    <form class="modal" @submit.prevent="assignRoles">
      <div class="modal-head">
        <h2>分配角色：{{ userRoleEditor.username }}</h2>
        <button class="ghost" type="button" :disabled="busy" @click="userRoleEditor = null">
          关闭
        </button>
      </div>
      <p class="muted">角色可多选。保存后该用户所有旧会话将失效，需要重新登录。</p>
      <label v-for="entry in roles" :key="entry.role.id" class="check"
        ><input v-model="userRoleEditor.roleIds" type="checkbox" :value="entry.role.id" />{{
          entry.role.name
        }}</label
      >
      <p class="error">{{ message }}</p>
      <div class="actions">
        <button :disabled="busy || !userRoleEditor.roleIds.length">保存角色</button>
      </div>
    </form>
  </div>
  <div v-if="roleEditor" class="overlay">
    <form class="modal" @submit.prevent="savePermissions">
      <div class="modal-head">
        <h2>{{ roleEditor.role.name }} · 功能权限</h2>
        <button class="ghost" type="button" :disabled="busy" @click="roleEditor = null">
          关闭
        </button>
      </div>
      <fieldset v-for="group in groups" :key="group">
        <legend>{{ groupNames[group] }}</legend>
        <label
          v-for="p in permissions.filter((item) => item.category === group)"
          :key="p.code"
          class="permission-check"
          ><input v-model="roleEditor.permissions" type="checkbox" :value="p.code" /><span
            >{{ p.name }}<small>{{ p.code }}</small></span
          ></label
        >
      </fieldset>
      <p class="error">{{ message }}</p>
      <div class="actions"><button :disabled="busy">保存并使相关旧会话失效</button></div>
    </form>
  </div>
</template>
