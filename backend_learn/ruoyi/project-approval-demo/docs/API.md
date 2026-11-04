# HTTP接口

后端8081，前端开发代理/api；除登录和简要健康检查外均需要Authorization: Bearer JWT。

响应外壳：`{code,msg,data,requestId}`。成功code=200；HTTP错误状态与code保持一致。列表data为`{rows,total,pageNum,pageSize}`。

| 方法 | 路径 | 功能/权限 |
| --- | --- | --- |
| POST | /api/auth/login | 登录；username、password |
| GET | /api/auth/me | 当前身份及权限 |
| POST | /api/auth/logout | 删除当前Redis会话 |
| GET | /api/auth/sessions | 本账号会话及TTL |
| DELETE | /api/auth/sessions/{sessionId} | 撤销自己的指定会话 |
| PUT | /api/auth/password | oldPassword、newPassword |
| GET | /api/projects | 本人列表；approval:report:list |
| GET | /api/review-tasks | 待办/已办；approval:review:list |
| GET | /api/projects/reviewers?projectId=可选 | 获取材料所属单位的候选人 |
| GET | /api/projects/{id}?roundNo=可选 | 本人当前材料或自己获分配轮次的快照 |
| POST | /api/projects | 新增；name、code、amount、material、version=0 |
| PUT | /api/projects/{id} | 编辑；同上，version为打开表单时的值 |
| POST | /api/projects/{id}/submit | reviewers数组、version、requestId |
| POST | /api/projects/{id}/review | stepId、version、approved布尔值、opinion |
| POST | /api/projects/{id}/withdraw | version、reason |
| DELETE | /api/projects/{id}?version=版本 | 逻辑删除从未提交的草稿 |
| GET | /api/admin/users?page=1&size=10 | system:user:list |
| GET | /api/admin/organizations | system:user:list或create |
| POST | /api/admin/users | username、displayName、orgId、password、roleIds；须同时有create和assign权限 |
| PUT | /api/admin/users/{id}/roles | roleIds；system:user:assign |
| PUT | /api/admin/users/{id}/enabled?enabled=false | system:user:disable |
| DELETE | /api/admin/users/{id}/sessions | system:user:revoke |
| GET | /api/admin/roles | system:role:list |
| GET | /api/admin/permissions | system:role:list |
| PUT | /api/admin/roles/{id}/permissions | permissions字符串数组；system:role:edit |
| GET | /api/admin/audit-logs?page=1&size=10&category=AUTH | system:audit:list |
| GET | /actuator/health | 简要健康状态，匿名不返回依赖细节 |

角色内置管理员不可通过接口修改权限；内置admin账号不能停用或改角色，避免把系统锁死。业务填报人不能审核自己。

默认分页page=1、size=10，size最大50。待办查询taskState=PENDING或PROCESSED；已办列表按轮次返回，详情应带对应visibleRoundNo。
