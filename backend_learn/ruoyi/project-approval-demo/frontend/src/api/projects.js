import { http } from './http'
export const projectApi = {
  list: (mode, query) =>
    http((mode === 'report' ? '/projects' : '/review-tasks') + '?' + new URLSearchParams(query)),
  detail: (id, roundNo) =>
    http('/projects/' + encodeURIComponent(id) + (roundNo ? '?roundNo=' + roundNo : '')),
  reviewers: (projectId) =>
    http('/projects/reviewers' + (projectId ? '?projectId=' + encodeURIComponent(projectId) : '')),
  create: (body) => http('/projects', 'POST', body),
  update: (id, body) => http('/projects/' + id, 'PUT', body),
  submit: (id, body) => http('/projects/' + id + '/submit', 'POST', body),
  review: (id, body) => http('/projects/' + id + '/review', 'POST', body),
  withdraw: (id, body) => http('/projects/' + id + '/withdraw', 'POST', body),
  remove: (id, version) => http('/projects/' + id + '?version=' + version, 'DELETE'),
}
