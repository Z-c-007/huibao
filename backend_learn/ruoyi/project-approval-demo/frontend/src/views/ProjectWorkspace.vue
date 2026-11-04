<script setup>
import { ref, onMounted } from 'vue'
import { projectApi } from '../api/projects'
import { can } from '../stores/session'
import { useAction } from '../composables/useAction'
import ProjectEditor from '../components/ProjectEditor.vue'
import ProjectDetail from '../components/ProjectDetail.vue'
const props = defineProps({ mode: { type: String, required: true } })
const rows = ref([]),
  total = ref(0),
  page = ref(1),
  status = ref(''),
  taskState = ref('PENDING')
const editor = ref(null),
  selected = ref(null)
const { busy, message, run } = useAction()
const names = {
  DRAFT: '草稿',
  PENDING: '待审核',
  APPROVED: '审批通过',
  REJECTED: '已驳回',
  CANCELLED: '已撤回',
}
async function load() {
  const data = await projectApi.list(props.mode, {
    page: page.value,
    size: 10,
    status: status.value,
    taskState: taskState.value,
  })
  rows.value = data.rows
  total.value = data.total
}
function changePage(offset = 0) {
  page.value = offset === 0 ? 1 : page.value + offset
  return run(load)
}
async function changed() {
  editor.value = null
  await run(load)
}
async function remove(row) {
  await run(async () => {
    if (!confirm('确认删除从未提交过的草稿？')) return
    await projectApi.remove(row.id, row.version)
    await load()
  })
}
async function withdrawn(row) {
  await run(async () => {
    const reason = prompt('请输入撤回原因，审批历史将保留')
    if (!reason?.trim()) return
    await projectApi.withdraw(row.id, { version: row.version, reason })
    await load()
  })
}
onMounted(() => run(load))
</script>
<template>
  <header>
    <div>
      <div class="eyebrow">{{ mode === 'report' ? 'MY REPORTS' : 'APPROVAL DESK' }}</div>
      <h1>{{ mode === 'report' ? '项目信息填报' : '项目信息审核' }}</h1>
      <p>
        {{
          mode === 'report'
            ? '管理本人材料，跟踪每一轮提交与审批。'
            : '仅查看实际流转到自己的材料快照，同级任意一人通过即可。'
        }}
      </p>
    </div>
    <button v-if="mode === 'report' && can('approval:report:add')" @click="editor = { id: null }">
      ＋ 新增材料
    </button>
  </header>
  <p v-if="message" class="notice" role="alert">{{ message }}</p>
  <section class="panel">
    <div class="toolbar">
      <label v-if="mode === 'review'"
        >任务类型<select
          v-model="taskState"
          :disabled="busy"
          @change="changePage()"
        >
          <option value="PENDING">我的待办</option>
          <option value="PROCESSED">已办 / 已由他人处理</option>
        </select></label
      >
      <label
        >材料状态<select
          v-model="status"
          :disabled="busy"
          @change="changePage()"
        >
          <option value="">全部状态</option>
          <option
            v-for="s in mode === 'report'
              ? ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED']
              : ['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED']"
            :key="s"
            :value="s"
          >
            {{ names[s] }}
          </option>
        </select></label
      >
      <button class="secondary" :disabled="busy" @click="run(load)">刷新列表</button
      ><span class="muted">共 {{ total }} {{ mode === 'review' ? '个提交轮次' : '份材料' }}</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>项目 / 编号</th>
            <th>建设单位</th>
            <th>金额（万元）</th>
            <th>状态 / 当前节点</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id + ':' + (row.visibleRoundNo || 0)">
            <td>
              <strong>{{ row.projectName }}</strong
              ><small
                >{{ row.projectCode
                }}<template v-if="row.visibleRoundNo">
                  · 第{{ row.visibleRoundNo }}轮</template
                ></small
              >
            </td>
            <td>
              {{ row.orgName || '历史记录' }}<small>{{ row.creatorName }}</small>
            </td>
            <td>{{ row.amount ?? '—' }}</td>
            <td>
              <span class="badge" :class="row.status">{{ names[row.status] }}</span
              ><small>{{ row.currentOrgName || '—' }}</small>
            </td>
            <td>
              <button
                v-if="can(mode === 'report' ? 'approval:report:query' : 'approval:review:query')"
                class="link"
                @click="selected = row"
              >
                查看详情
              </button>
              <template v-if="mode === 'report'"
                ><button
                  v-if="['DRAFT', 'REJECTED'].includes(row.status) && can('approval:report:edit')"
                  class="link"
                  @click="editor = { id: row.id }"
                >
                  编辑 / 提交</button
                ><button
                  v-if="row.status === 'PENDING' && can('approval:report:withdraw')"
                  class="link"
                  :disabled="busy"
                  @click="withdrawn(row)"
                >
                  撤回</button
                ><button
                  v-if="
                    row.status === 'DRAFT' && row.roundNo === 0 && can('approval:report:delete')
                  "
                  class="link danger"
                  :disabled="busy"
                  @click="remove(row)"
                >
                  删除
                </button></template
              >
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td class="empty" colspan="5">
              暂无数据。{{
                mode === 'review'
                  ? '材料流转到你的节点后才会出现在待办中。'
                  : '可新增材料开始填报。'
              }}
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
  <ProjectEditor v-if="editor" :project-id="editor.id" @close="editor = null" @saved="changed" />
  <ProjectDetail
    v-if="selected"
    :project-id="selected.id"
    :round-no="selected.visibleRoundNo"
    @close="selected = null"
    @changed="run(load)"
  />
</template>
