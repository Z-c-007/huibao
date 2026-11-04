import { http } from './http'
export const adminApi = {
  users: (page = 1) => http(`/admin/users?page=${page}&size=10`),
  organizations: () => http('/admin/organizations'),
  roles: () => http('/admin/roles'),
  permissions: () => http('/admin/permissions'),
  createUser: (body) => http('/admin/users', 'POST', body),
  assign: (id, roleIds) => http(`/admin/users/${id}/roles`, 'PUT', { roleIds }),
  enabled: (id, enabled) => http(`/admin/users/${id}/enabled?enabled=${enabled}`, 'PUT'),
  revoke: (id) => http(`/admin/users/${id}/sessions`, 'DELETE'),
  rolePermissions: (id, permissions) =>
    http(`/admin/roles/${id}/permissions`, 'PUT', { permissions }),
  logs: (page, category) => http(`/admin/audit-logs?page=${page}&size=10&category=${category}`),
}
