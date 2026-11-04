-- V2只读学习查询；一条条执行并对照Mapper XML。
USE project_approval_demo;

-- 用户属于哪些角色：用户与角色是多对多。
SELECT
    u.id,
    u.username,
    u.display_name,
    o.name AS org_name,
    r.code AS role_code,
    r.name AS role_name
FROM
    app_user u
    JOIN organization o ON o.id = u.org_id
    JOIN app_user_role ur ON ur.user_id = u.id
    JOIN app_role r ON r.id = ur.role_id
ORDER BY
    u.id,
    r.id;

-- 用户最终有哪些有效功能权限：角色停用后不参与。
SELECT DISTINCT
    u.username,
    r.code AS role_code,
    p.code AS permission_code,
    p.name
FROM
    app_user u
    JOIN app_user_role ur ON ur.user_id = u.id
    JOIN app_role r ON r.id = ur.role_id
    AND r.enabled = 1
    JOIN app_role_permission rp ON rp.role_id = r.id
    JOIN app_permission p ON p.code = rp.permission_code
WHERE
    u.username = 'report_b'
ORDER BY
    p.code;

-- 核对账号安全版本；JWT和Redis会话中的authVersion须与这里一致。
SELECT
    u.username,
    u.enabled,
    s.auth_version
FROM
    app_user u
    JOIN app_user_security s ON s.user_id = u.id
ORDER BY
    u.id;

-- 主表只存当前数据。未提交草稿没有current_step_id，LEFT JOIN保留这些记录。
SELECT
    p.id,
    p.project_code,
    p.project_name,
    p.status,
    p.version,
    p.round_no,
    u.display_name AS creator,
    o.name AS report_org,
    n.org_name AS current_review_org
FROM
    project p
    JOIN app_user u ON u.id = p.creator_id
    JOIN organization o ON o.id = p.org_id
    LEFT JOIN approval_step n ON n.id = p.current_step_id
WHERE
    p.deleted = 0
ORDER BY
    p.updated_at DESC;

-- 每次提交的快照，与当前主表分开；旧版本没有的数据不伪造。
SELECT
    project_id,
    round_no,
    project_name,
    amount,
    material,
    status,
    snapshot_available,
    submitted_at,
    closed_at
FROM
    project_submission
ORDER BY
    project_id,
    round_no;

-- 一轮多个节点，一个节点多个候选人，因此联查会出现多行，不是材料重复保存。
SELECT
    p.project_code,
    n.round_no,
    n.seq,
    n.org_name,
    n.status AS node_status,
    a.display_name AS candidate,
    a.status AS candidate_status,
    n.actor_name,
    n.opinion,
    n.started_at,
    n.acted_at
FROM
    project p
    JOIN approval_step n ON n.project_id = p.id
    JOIN approval_assignee a ON a.step_id = n.id
ORDER BY
    p.project_code,
    n.round_no,
    n.seq,
    a.user_id;

-- 真正待办必须同时满足：材料当前节点、节点已激活、候选任务待处理。
SELECT
    u.username,
    p.project_code,
    p.project_name,
    n.round_no,
    n.org_name
FROM
    app_user u
    JOIN approval_assignee a ON a.user_id = u.id
    AND a.status = 'PENDING'
    JOIN approval_step n ON n.id = a.step_id
    AND n.status = 'PENDING'
    JOIN project p ON p.current_step_id = n.id
    AND p.status = 'PENDING'
    AND p.deleted = 0
ORDER BY
    u.id,
    p.project_code;

-- 业务事务轨迹：状态和版本一起变化。
SELECT
    p.project_code,
    e.round_no,
    e.action,
    e.actor_name,
    e.before_status,
    e.after_status,
    e.before_version,
    e.after_version,
    e.note,
    e.created_at
FROM
    project_event e
    JOIN project p ON p.id = e.project_id
ORDER BY
    e.id;

-- 登录/操作审计，不包含密码、JWT或完整请求体。
SELECT
    category,
    operation,
    actor_name,
    success,
    http_status,
    request_id,
    message,
    created_at
FROM
    app_audit_log
ORDER BY
    id DESC
LIMIT
    50;

-- 直接用SQL修改角色权限时，需在同一事务中递增相关用户auth_version，令旧会话失效。
-- 日常优先通过管理员页面操作，Java服务会自动做版本更新与会话清理。
