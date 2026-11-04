<script setup>
import { ref, onMounted } from 'vue'
import { projectApi } from '../api/projects'
import { useAction } from '../composables/useAction'
const props = defineProps({
  projectId: { type: String, required: true },
  roundNo: { type: Number, default: null },
})
const emit = defineEmits(['close', 'changed'])
const detail = ref(null),
  opinion = ref('')
const { busy, message, run } = useAction()
const names = {
  DRAFT: '草稿',
  PENDING: '待审核',
  APPROVED: '审批通过',
  REJECTED: '已驳回',
  WAITING: '尚未流转',
  PASSED: '本级通过',
  CANCELLED: '已取消 / 已撤回',
  CLOSED: '同级其他人已办理',
}
async function load() {
  detail.value = await projectApi.detail(props.projectId, props.roundNo)
}
async function decide(approved) {
  await run(async () => {
    if (!approved && !opinion.value.trim()) throw new Error('驳回必须填写意见')
    if (!confirm(approved ? '确认通过当前节点？' : '确认驳回填报人？')) return
    const p = detail.value.project
    await projectApi.review(p.id, {
      stepId: p.currentStepId,
      version: p.version,
      approved,
      opinion: opinion.value,
    })
    await load()
    emit('changed')
    message.value = approved ? '本级已通过，流程已更新' : '已驳回填报人'
  })
}
async function withdraw() {
  await run(async () => {
    const reason = prompt('请输入撤回原因')
    if (!reason?.trim()) return
    await projectApi.withdraw(props.projectId, { version: detail.value.project.version, reason })
    await load()
    emit('changed')
  })
}
function candidateNames(step) {
  return detail.value.assignees
    .filter((a) => a.stepId === step.id)
    .map((a) => `${a.displayName}（${names[a.status] || a.status}）`)
    .join('、')
}
onMounted(() => run(load))
</script>
<template>
  <div class="overlay">
    <section class="modal wide">
      <div class="modal-head">
        <h2>材料与审批详情</h2>
        <button class="ghost" :disabled="busy" @click="emit('close')">关闭</button>
      </div>
      <p class="error" role="alert">{{ message }}</p>
      <template v-if="detail"
        ><span class="badge" :class="detail.project.status">{{
          names[detail.project.status]
        }}</span>
        <h2>{{ detail.project.projectName }}</h2>
        <p v-if="detail.notice" class="notice">{{ detail.notice }}</p>
        <div class="facts">
          <span>编号：{{ detail.project.projectCode || '—' }}</span
          ><span>建设单位：{{ detail.project.orgName || '—' }}</span
          ><span>填报人：{{ detail.project.creatorName || '—' }}</span
          ><span>金额：{{ detail.project.amount ?? '—' }} 万元</span>
        </div>
        <h3>材料说明</h3>
        <p class="material">{{ detail.project.material || '该历史轮次没有材料快照。' }}</p>
        <h3>提交快照</h3>
        <details v-for="s in detail.submissions" :key="s.id" class="snapshot">
          <summary>
            第 {{ s.roundNo }} 轮 · {{ names[s.status] }} ·
            {{ s.submittedAt?.replace('T', ' ') || '升级前时间未记录' }}
          </summary>
          <template v-if="s.snapshotAvailable"
            ><p>{{ s.projectName }} · {{ s.projectCode }} · {{ s.amount }} 万元</p>
            <p>{{ s.submitterName }} / {{ s.orgName }}</p>
            <p class="material">{{ s.material }}</p></template
          >
          <p v-else>旧版本未保存快照，不使用当前材料伪造历史内容。</p>
        </details>
        <h3>审批路径与办理情况</h3>
        <p v-if="!detail.steps.length" class="muted">尚未提交。</p>
        <article v-for="step in detail.steps" :key="step.id" class="step">
          <div>
            <strong>第 {{ step.roundNo }} 轮 · {{ step.orgName }}</strong
            ><span class="badge">{{ names[step.status] }}</span>
          </div>
          <p>{{ candidateNames(step) }}</p>
          <p v-if="step.actorName">
            办理人：{{ step.actorName }} · {{ step.actedAt?.replace('T', ' ') }}
          </p>
          <p v-if="step.opinion">意见：{{ step.opinion }}</p>
        </article>
        <section v-if="detail.canReview" class="review-box">
          <h3>办理当前节点</h3>
          <textarea
            v-model="opinion"
            maxlength="1000"
            rows="3"
            placeholder="审批意见，驳回时必填"
            :disabled="busy"
          ></textarea>
          <div class="actions">
            <button class="secondary danger" :disabled="busy" @click="decide(false)">
              驳回填报人</button
            ><button :disabled="busy" @click="decide(true)">通过本级审批</button>
          </div>
        </section>
        <div class="actions">
          <button v-if="detail.canWithdraw" class="secondary" :disabled="busy" @click="withdraw">
            撤回材料</button
          ><button class="secondary" :disabled="busy" @click="run(load)">刷新详情</button>
        </div>
        <details>
          <summary>业务流转记录</summary>
          <div v-for="event in detail.events" :key="event.id" class="event-row">
            <strong>{{ event.action }}</strong> · {{ event.actorName }} ·
            {{ event.createdAt?.replace('T', ' ') }}
            <p>
              {{ event.beforeStatus || '新建' }} → {{ event.afterStatus || '历史状态未记录' }}；版本
              {{ event.beforeVersion ?? '—' }} → {{ event.afterVersion ?? '—' }}；{{ event.note }}
            </p>
          </div>
        </details>
      </template>
    </section>
  </div>
</template>
