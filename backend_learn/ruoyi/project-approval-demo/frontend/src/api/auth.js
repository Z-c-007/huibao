import { http } from './http'
export const authApi = {
  login: (body) => http('/auth/login', 'POST', body),
  me: () => http('/auth/me'),
  logout: () => http('/auth/logout', 'POST'),
  sessions: () => http('/auth/sessions'),
  revoke: (id) => http('/auth/sessions/' + encodeURIComponent(id), 'DELETE'),
  password: (body) => http('/auth/password', 'PUT', body),
}
