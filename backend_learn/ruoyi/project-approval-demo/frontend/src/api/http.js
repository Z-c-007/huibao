import { session, signedOut } from '../stores/session'
export class ApiError extends Error {
  constructor(status, message, requestId) {
    super(message)
    this.status = status
    this.requestId = requestId
  }
}
// 所有业务请求走同一个入口：统一Bearer、超时、401/403和requestId处理。
export async function http(path, method = 'GET', data) {
  const abort = new AbortController()
  const timer = setTimeout(() => abort.abort(), 15000)
  try {
    const response = await fetch('/api' + path, {
      method,
      signal: abort.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(session.token && path !== '/auth/login'
          ? { Authorization: 'Bearer ' + session.token }
          : {}),
      },
      ...(data === undefined ? {} : { body: JSON.stringify(data) }),
    })
    const result = await response.json().catch(() => null)
    const requestId = result?.requestId || response.headers.get('X-Request-Id')
    if (!response.ok) {
      const message = result?.msg || `请求失败（${response.status}）`
      if (response.status === 401 && path !== '/auth/login') signedOut(message)
      throw new ApiError(response.status, message, requestId)
    }
    return result.data
  } catch (error) {
    if (error.name === 'AbortError')
      throw new ApiError(0, '请求超时，操作结果尚未确认，请刷新状态或重试同一提交')
    if (error instanceof ApiError) throw error
    throw new ApiError(0, '无法连接后端，请检查后端日志与启动状态')
  } finally {
    clearTimeout(timer)
  }
}
export function errorText(error) {
  return error.message + (error.requestId ? `（请求ID：${error.requestId}）` : '')
}
