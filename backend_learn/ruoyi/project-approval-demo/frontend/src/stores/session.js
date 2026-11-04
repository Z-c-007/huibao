import { reactive } from 'vue'
const KEY = 'approval-v2-token'
// V1随机Token与V2 JWT协议不同，升级后必须重新登录。
sessionStorage.removeItem('approval-token')
export const session = reactive({
  token: sessionStorage.getItem(KEY) || '',
  user: null,
  notice: '',
})
export function signedIn(token, user) {
  session.token = token
  session.user = user
  session.notice = ''
  sessionStorage.setItem(KEY, token)
}
export function signedOut(message = '') {
  sessionStorage.removeItem(KEY)
  session.token = ''
  session.user = null
  session.notice = message
}
export function can(permission) {
  return session.user?.permissions?.includes(permission) || false
}
