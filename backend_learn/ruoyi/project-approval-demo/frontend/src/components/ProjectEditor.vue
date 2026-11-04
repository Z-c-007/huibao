<script setup>
import { ref, reactive, onMounted } from 'vue'
import { projectApi } from '../api/projects'
import { session, can } from '../stores/session'
import { useAction } from '../composables/useAction'
const props = defineProps({ projectId: { type: String, default: null } })
const emit = defineEmits(['close', 'saved'])
const form = reactive({
  id: props.projectId,
  name: '',
  code: '',
  amount: '0.00',
  material: '',
  version: 0,
  reviewers: [],
})
const candidates = ref([]),
  orgName = ref(session.user.orgName),
  ready = ref(false),
  pending = ref(null)
const { busy, message, run } = useAction()
let fingerprint = ''
const body = () => ({
  name: form.name,
  code: form.code,
  amount: form.amount,
  material: form.material,
  version: form.version,
})
const content = () =>
  JSON.stringify({
    name: form.name,
    code: form.code,
    amount: String(form.amount),
    material: form.material,
  })
onMounted(() =>
  run(async () => {
    if (form.id) {
      const detail = await projectApi.detail(form.id)
      if (!detail.canEdit) throw new Error('当前材料不可编辑')
      const p = detail.project
      Object.assign(form, {
        name: p.projectName,
        code: p.projectCode,
        amount: String(p.amount),
        material: p.material,
        version: p.version,
      })
      orgName.value = p.orgName
      fingerprint = content()
    }
    candidates.value = await projectApi.reviewers(form.id)
    ready.value = true
  }),
)
async function submitPending() {
  try {
    await projectApi.submit(form.id, pending.value)
    emit('saved')
  } catch (error) {
    if (error.status >= 400 && error.status < 500) pending.value = null
    throw error
  }
}
async function save(submit) {
  await run(async () => {
    if (!form.name.trim() || !form.code.trim() || !form.material.trim())
      throw new Error('请填写完整材料信息')
    if (!form.id || content() !== fingerprint) {
      const saved = form.id
        ? await projectApi.update(form.id, body())
        : await projectApi.create(body())
      form.id = saved.id
      form.version = saved.version
      fingerprint = content()
    }
    if (!submit) {
      emit('saved')
      return
    }
    // 提交结果未知时保留整个请求，重试不先保存、不换版本号，数据库才能识别相同提交。
    pending.value = {
      version: form.version,
      reviewers: [...form.reviewers],
      requestId: crypto.randomUUID(),
    }
    await submitPending()
  })
}
</script>
<template>
  <div class="overlay">
    <form class="modal" @submit.prevent="save(false)">
      <div class="modal-head">
        <h2>{{ form.id ? '编辑项目材料' : '新增项目材料' }}</h2>
        <button type="button" class="ghost" :disabled="busy" @click="emit('close')">关闭</button>
      </div>
      <fieldset class="plain-fields" :disabled="busy || !ready || !!pending">
        <div class="grid">
          <label>项目名称<input v-model="form.name" required maxlength="100" /></label
          ><label
            >项目编号<input
              v-model="form.code"
              required
              minlength="3"
              maxlength="40"
              pattern="[A-Za-z0-9][A-Za-z0-9_-]{2,39}" /></label
          ><label
            >金额（万元）<input
              v-model="form.amount"
              type="number"
              min="0"
              max="999999999999.99"
              step="0.01"
              required /></label
          ><label>建设单位<input :value="orgName" disabled /></label>
        </div>
        <label
          >材料说明<textarea v-model="form.material" required maxlength="4000" rows="5"></textarea>
        </label>
        <fieldset v-if="can('approval:report:submit')">
          <legend>本级审批人（多人或签）</legend>
          <label v-for="u in candidates" :key="u.id" class="check"
            ><input v-model="form.reviewers" type="checkbox" :value="u.id" />{{
              u.displayName
            }}</label
          >
          <p class="muted">
            不勾选则跳过本级，向上寻找有效审批人；填报人本人不能审批自己的材料。名单在本轮提交时冻结。
          </p>
        </fieldset>
      </fieldset>
      <p class="error" role="alert">{{ message }}</p>
      <p v-if="pending" class="muted">
        提交结果尚未确认。重试会复用同一请求标识，不会重复创建审批轮次；也可以关闭后刷新列表确认。
      </p>
      <div class="actions">
        <template v-if="!pending"
          ><button
            class="secondary"
            :disabled="
              busy ||
              !ready ||
              (form.id ? !can('approval:report:edit') : !can('approval:report:add'))
            "
          >
            保存材料</button
          ><button
            v-if="can('approval:report:submit')"
            type="button"
            :disabled="busy || !ready"
            @click="save(true)"
          >
            保存并提交
          </button></template
        ><button v-else type="button" :disabled="busy" @click="run(submitPending)">
          重试同一提交
        </button>
      </div>
    </form>
  </div>
</template>
