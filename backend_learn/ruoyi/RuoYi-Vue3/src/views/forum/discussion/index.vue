<template>
  <div class="app-container discussion-page">
    <header class="discussion-header">
      <div>
        <div class="eyebrow">系统使用反馈 / 讨论区</div>
        <h1>一起把系统用得更好</h1>
        <p>记录实际使用中的问题，让建议得到回应。</p>
      </div>
      <div class="current-user"><el-icon><User /></el-icon><span>{{ userStore.nickName || userStore.name }}</span></div>
    </header>

    <el-skeleton v-if="initialLoading" :rows="6" animated />
    <el-result v-else-if="initialError" icon="error" title="讨论区暂时无法加载" sub-title="请稍后重试，或联系维护人员。">
      <template #extra><el-button type="primary" @click="initialize">重新加载</el-button></template>
    </el-result>
    <template v-else-if="topic">
      <section class="topic-panel">
        <el-tag effect="plain">讨论主题</el-tag>
        <h2>{{ topic.title }}</h2>
        <p>{{ topic.description }}</p>
      </section>

      <section v-hasPermi="['forum:comment:add']" class="composer" aria-label="发表评论">
        <h3>说说你的想法</h3>
        <el-input v-model="content" type="textarea" :rows="3" maxlength="200" show-word-limit placeholder="描述遇到的问题或建议（最多200字）" aria-label="评论内容" />
        <div class="composer-actions"><span>请勿填写密码、联系方式等敏感信息。</span><el-button type="primary" :loading="submitting" @click="submitComment">发表评论</el-button></div>
      </section>

      <section class="comments-section">
        <div class="section-heading"><h2>全部评论 <span>{{ total }}</span></h2><el-button :loading="listLoading" @click="loadComments">刷新评论</el-button></div>
        <div v-loading="listLoading" class="comments-body">
          <el-result v-if="listError" icon="warning" title="评论加载失败"><template #extra><el-button @click="loadComments">重试</el-button></template></el-result>
          <el-empty v-else-if="!comments.length" description="还没有评论，来分享第一条建议吧" />
          <article v-for="comment in comments" v-else :key="comment.commentId" class="comment-item">
            <div class="comment-avatar" aria-hidden="true">{{ comment.authorName?.slice(0, 1) || '成' }}</div>
            <div class="comment-main">
              <div class="comment-meta"><strong>{{ comment.authorName }}</strong><time>{{ comment.createTime }}</time></div>
              <!-- Vue文本插值会转义内容；不把用户输入当HTML执行。 -->
              <p class="plain-content">{{ comment.content }}</p>
              <div class="comment-actions">
                <el-button link type="primary" @click="toggleReplies(comment)">{{ threads[comment.commentId]?.open ? '收起回复' : '查看回复' }}</el-button>
                <el-button v-hasPermi="['forum:reply:add']" link type="primary" @click="openReply(comment)">维护人员回复</el-button>
                <el-button v-hasPermi="['forum:comment:edit']" link type="primary" @click="openEdit(comment, false)">编辑评论</el-button>
                <el-button v-hasPermi="['forum:comment:remove']" link type="danger" @click="deleteEntry(comment, false)">删除评论</el-button>
              </div>
              <div v-if="threads[comment.commentId]?.open" v-loading="threads[comment.commentId].loading" class="reply-list">
                <p v-if="threads[comment.commentId].error" class="thread-empty">回复加载失败。<el-button link type="primary" @click="loadReplies(comment.commentId)">重新加载</el-button></p>
                <p v-else-if="!threads[comment.commentId].rows.length" class="thread-empty">暂无回复</p>
                <div v-for="reply in threads[comment.commentId].rows" :key="reply.commentId" class="reply-item">
                  <div class="comment-meta"><strong>{{ reply.authorName }}</strong><el-tag size="small" type="success">维护回复</el-tag><time>{{ reply.createTime }}</time></div>
                  <p class="plain-content">{{ reply.content }}</p>
                  <div v-if="String(reply.authorId) === String(userStore.id)" class="comment-actions">
                    <el-button v-hasPermi="['forum:reply:edit']" link type="primary" @click="openEdit(reply, true)">编辑我的回复</el-button>
                    <el-button v-hasPermi="['forum:reply:remove']" link type="danger" @click="deleteEntry(reply, true)">删除我的回复</el-button>
                  </div>
                </div>
                <pagination v-if="threads[comment.commentId].total > 10" :total="threads[comment.commentId].total" v-model:page="threads[comment.commentId].pageNum" :limit="10" :page-sizes="[10]" @pagination="loadReplies(comment.commentId)" />
              </div>
            </div>
          </article>
        </div>
        <pagination v-show="total > 0" :total="total" v-model:page="query.pageNum" v-model:limit="query.pageSize" :page-sizes="[10, 20, 50]" @pagination="loadComments" />
      </section>
    </template>

    <el-dialog v-model="replyVisible" title="维护人员回复" width="min(560px, 92vw)" :close-on-click-modal="false" @closed="resetReply">
      <blockquote class="reply-context">{{ replyTarget?.content }}</blockquote>
      <el-input v-model="replyContent" type="textarea" :rows="4" maxlength="200" show-word-limit placeholder="填写回复（最多200字）" aria-label="回复内容" />
      <template #footer><el-button :disabled="replySubmitting" @click="replyVisible = false">取消</el-button><el-button type="primary" :loading="replySubmitting" @click="submitReply">提交回复</el-button></template>
    </el-dialog>
    <el-dialog v-model="editVisible" title="编辑内容" width="min(560px, 92vw)" :close-on-click-modal="false" :close-on-press-escape="!editSubmitting" :show-close="!editSubmitting">
      <p>仅修改文字内容，作者和创建时间保持原值。</p>
      <el-input v-model="editContent" type="textarea" :rows="4" maxlength="200" show-word-limit aria-label="编辑内容" />
      <template #footer><el-button :disabled="editSubmitting" @click="editVisible = false">取消</el-button><el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存修改</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup name="ForumDiscussion">
import { User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import useUserStore from '@/store/modules/user'
import { getTopic, listComments, listReplies, addComment, addReply, editEntry, removeEntry } from '@/api/forum/discussion'

const userStore = useUserStore()
const topic = ref(null)
const comments = ref([])
const total = ref(0)
const content = ref('')
const query = reactive({ pageNum: 1, pageSize: 10 })
const threads = reactive({})
const initialLoading = ref(true)
const initialError = ref(false)
const listLoading = ref(false)
const listError = ref(false)
const submitting = ref(false)
const replyVisible = ref(false)
const replySubmitting = ref(false)
const replyTarget = ref(null)
const replyContent = ref('')

// 页面只通过API模块访问后端，沿用若依request统一处理错误；catch只设置本页状态。
async function initialize() {
  initialLoading.value = true
  initialError.value = false
  try {
    const result = await getTopic()
    topic.value = result.data
    await loadComments()
  } catch {
    initialError.value = true
  } finally {
    initialLoading.value = false
  }
}

async function loadComments() {
  if (!topic.value || listLoading.value) return
  listLoading.value = true
  listError.value = false
  try {
    const result = await listComments({ topicId: topic.value.topicId, ...query })
    comments.value = result.rows
    total.value = result.total
    // 刷新后不保留旧分页的回复缓存，回复只在用户展开时查询。
    Object.keys(threads).forEach(key => delete threads[key])
  } catch {
    listError.value = true
  } finally {
    listLoading.value = false
  }
}

function validateText(value) {
  const text = value.trim()
  if (!text) { ElMessage.warning('内容不能为空'); return null }
  if (text.length > 200) { ElMessage.warning('内容不能超过200个字符'); return null }
  return text
}

async function submitComment() {
  const text = validateText(content.value)
  if (!text || submitting.value) return
  submitting.value = true
  try {
    await addComment({ topicId: topic.value.topicId, content: text })
    content.value = ''
    query.pageNum = 1
    ElMessage.success('评论已发表')
    await loadComments()
  } catch {
    // request已经显示接口错误；保留输入，便于重试。
  } finally {
    submitting.value = false
  }
}

async function toggleReplies(comment) {
  const id = comment.commentId
  if (threads[id]?.open) { threads[id].open = false; return }
  if (!threads[id]) threads[id] = { open: true, rows: [], total: 0, pageNum: 1, loading: false, error: false }
  threads[id].open = true
  await loadReplies(id)
}

async function loadReplies(id) {
  const thread = threads[id]
  if (!thread || thread.loading) return
  thread.loading = true
  thread.error = false
  try {
    const result = await listReplies(id, { topicId: topic.value.topicId, pageNum: thread.pageNum, pageSize: 10 })
    thread.rows = result.rows
    thread.total = result.total
  } catch {
    thread.error = true
  } finally {
    thread.loading = false
  }
}

function openReply(comment) {
  replyTarget.value = comment
  replyContent.value = ''
  replyVisible.value = true
}
function resetReply() { replyTarget.value = null; replyContent.value = '' }

async function submitReply() {
  const text = validateText(replyContent.value)
  if (!text || replySubmitting.value || !replyTarget.value) return
  replySubmitting.value = true
  const parentId = replyTarget.value.commentId
  try {
    await addReply({ topicId: topic.value.topicId, parentId, content: text })
    replyVisible.value = false
    ElMessage.success('回复已发表')
    threads[parentId] = { open: true, rows: [], total: 0, pageNum: 1, loading: false, error: false }
    await loadReplies(parentId)
  } catch {
    // 保留编辑内容，不将失败误报为成功。
  } finally {
    replySubmitting.value = false
  }
}

const editVisible = ref(false)
const editSubmitting = ref(false)
const editContent = ref('')
const editTarget = ref(null)
const editingReply = ref(false)
const deleting = ref(false)

function openEdit(entry, reply) {
  editTarget.value = entry
  editingReply.value = reply
  editContent.value = entry.content
  editVisible.value = true
}

async function submitEdit() {
  const text = validateText(editContent.value)
  if (!text || editSubmitting.value || !editTarget.value) return
  editSubmitting.value = true
  const target = editTarget.value
  const reply = editingReply.value
  try {
    await editEntry(target.commentId, { topicId: topic.value.topicId, content: text }, reply)
    editVisible.value = false
    ElMessage.success('修改成功')
    if (reply) await loadReplies(target.parentId)
    else await loadComments()
  } catch {
    // 保留编辑内容，统一request负责提示错误。
  } finally {
    editSubmitting.value = false
  }
}

async function deleteEntry(entry, reply) {
  if (deleting.value) return
  deleting.value = true
  try {
    // 原评论删除会同时删除其全部回复，明确提示影响范围。
    await ElMessageBox.confirm(reply ? '确认删除这条自己的回复？删除后无法恢复。' : '确认删除这条评论及其全部回复？删除后无法恢复。', '删除确认', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    await removeEntry(entry.commentId, reply)
    ElMessage.success('删除成功')
    if (reply) {
      const thread = threads[entry.parentId]
      if (thread) thread.pageNum = 1
      await loadReplies(entry.parentId)
    } else {
      if (comments.value.length === 1 && query.pageNum > 1) query.pageNum--
      await loadComments()
    }
  } catch {
    // 取消确认或接口失败不显示成功；接口错误由request统一提示。
  } finally {
    deleting.value = false
  }
}

onMounted(initialize)
</script>

<style scoped lang="scss">
.discussion-page { max-width: 1140px; margin: 0 auto; padding: 32px; color: #243847; }
.discussion-header { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 28px;
  h1 { font-size: 28px; margin: 12px 0; font-weight: 600; } p { margin: 0; color: #72838e; font-size: 14px; }
}
.eyebrow { color: #16847b; font-size: 13px; font-weight: 600; letter-spacing: 1px; }
.current-user { display: flex; align-items: center; gap: 8px; color: #617483; font-size: 14px; white-space: nowrap; }
.topic-panel { background: #ecf6f3; padding: 25px 28px; border-left: 4px solid #16847b; border-radius: 5px;
  h2 { font-size: 21px; margin: 14px 0 10px; } p { margin: 0; font-size: 14px; line-height: 1.8; color: #5c7278; }
}
.composer { margin-top: 24px; padding: 24px; border: 1px solid #e3e9ed; background: #fff; border-radius: 6px; h3 { font-size: 16px; margin: 0 0 18px; } }
.composer-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 15px; span { font-size: 12px; color: #8999a2; } }
.comments-section { padding-top: 32px; }
.section-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; h2 { font-size: 18px; margin: 0; } h2 span { margin-left: 8px; font-size: 14px; color: #8a9ca5; font-weight: 400; } }
.comments-body { min-height: 100px; }
.comment-item { display: flex; gap: 14px; padding: 24px 0; border-bottom: 1px solid #e6ecef; }
.comment-avatar { width: 38px; height: 38px; background: #e3eeec; color: #317c70; display: grid; place-items: center; border-radius: 50%; flex: none; font-size: 15px; }
.comment-main { flex: 1; min-width: 0; }
.comment-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; font-size: 14px; time { font-size: 12px; color: #8c9ba5; } }
.plain-content { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14px; line-height: 1.9; margin: 12px 0 5px; }
.comment-actions { display: flex; flex-wrap: wrap; gap: 12px; }
.reply-list { margin-top: 12px; padding: 16px 20px; background: #f4f7f8; border-radius: 5px; min-height: 55px; }
.reply-item + .reply-item { margin-top: 18px; padding-top: 18px; border-top: 1px solid #e0e8eb; }
.thread-empty { color: #8a9aa4; font-size: 13px; margin: 0; }
.reply-context { margin: 0 0 20px; padding: 12px 16px; border-left: 3px solid #b3ccc7; background: #f3f7f6; color: #71847f; white-space: pre-wrap; overflow-wrap: anywhere; }
@media (max-width: 640px) { .discussion-page { padding: 20px 15px; } .discussion-header { align-items: flex-start; flex-direction: column; } .discussion-header h1 { font-size: 23px; } .composer-actions { align-items: flex-end; } .topic-panel { padding: 20px; } }
</style>
