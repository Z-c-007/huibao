import request from '@/utils/request'

// request 统一携带真实登录 token，并按若依规范处理业务错误与登录失效。
export function getTopic() {
  return request({ url: '/forum/topic', method: 'get' })
}

// 分页列表响应是 rows / total；主题及新增响应使用 data，不能混淆。
export function listComments(params) {
  return request({ url: '/forum/comments', method: 'get', params })
}

export function listReplies(commentId, params) {
  return request({ url: `/forum/comments/${commentId}/replies`, method: 'get', params })
}

// 不提交 authorId、authorName 或角色，由后端从登录身份确定作者。
export function addComment(data) {
  return request({ url: '/forum/comments', method: 'post', data })
}

export function addReply(data) {
  return request({ url: '/forum/replies', method: 'post', data })
}

// id是待操作记录自己的commentId，回复接口不传父评论编号。
export function editEntry(id, data, reply = false) {
  return request({ url: `/forum/${reply ? 'replies' : 'comments'}/${id}`, method: 'put', data })
}

export function removeEntry(id, reply = false) {
  return request({ url: `/forum/${reply ? 'replies' : 'comments'}/${id}`, method: 'delete' })
}
