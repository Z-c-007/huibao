-- 只读学习查询。请在DBeaver中将当前数据库切换为project_approval_demo。
USE project_approval_demo;

-- 1. 组织树：子公司与上级公司。一个组织可能没有父级，所以使用LEFT JOIN。
SELECT
    child.id,
    child.name AS org_name,
    parent.name AS parent_org
FROM
    organization child
    LEFT JOIN organization parent ON parent.id = child.parent_id
ORDER BY
    child.id;

-- 2. 业务身份表：这里的密码是不可直接还原的BCrypt哈希，不是明文。
SELECT
    u.id,
    u.username,
    u.display_name,
    u.role,
    o.name AS org_name,
    u.enabled
FROM
    app_user u
    JOIN organization o ON o.id = u.org_id
ORDER BY
    u.id;

-- 3. 项目、填报人、建设单位、当前审批单位。
-- 草稿/已结束材料没有当前节点，后两处LEFT JOIN保留这些材料。
SELECT
    p.id,
    p.project_code,
    p.project_name,
    p.amount,
    p.status,
    p.round_no,
    creator.display_name AS creator_name,
    org.name AS report_org,
    current_org.name AS current_review_org
FROM
    project p
    JOIN app_user creator ON creator.id = p.creator_id
    JOIN organization org ON org.id = p.org_id
    LEFT JOIN approval_step current_step ON current_step.id = p.current_step_id
    LEFT JOIN organization current_org ON current_org.id = current_step.org_id
ORDER BY
    p.created_at DESC;

-- 4. 多表查询：每份材料每一轮、每一级的候选人及实际办理人。
-- 一个节点两位候选人，会产生两行结果；不是项目被重复保存。
SELECT
    p.project_code,
    s.round_no,
    s.seq,
    o.name AS review_org,
    s.status AS step_status,
    candidate.display_name AS candidate_name,
    a.status AS candidate_status,
    actor.display_name AS actual_actor,
    s.opinion,
    s.acted_at
FROM
    project p
    JOIN approval_step s ON s.project_id = p.id
    JOIN organization o ON o.id = s.org_id
    JOIN approval_assignee a ON a.step_id = s.id
    JOIN app_user candidate ON candidate.id = a.user_id
    LEFT JOIN app_user actor ON actor.id = s.actor_id
ORDER BY
    p.project_code,
    s.round_no,
    s.seq,
    a.user_id;

-- 5. 当前待办：只统计当前激活节点中的候选人，未来节点不算待办。
SELECT
    u.username,
    u.display_name,
    COUNT(DISTINCT p.id) AS pending_projects
FROM
    app_user u
    LEFT JOIN approval_assignee a ON a.user_id = u.id
    AND a.status = 'PENDING'
    LEFT JOIN project p ON p.current_step_id = a.step_id
    AND p.status = 'PENDING'
WHERE
    u.role = 'REVIEWER'
GROUP BY
    u.id,
    u.username,
    u.display_name
ORDER BY
    u.id;

-- 6. 操作记录：包括草稿保存、提交、本级通过、驳回。
SELECT
    p.project_code,
    u.display_name AS operator_name,
    e.action,
    e.note,
    e.created_at
FROM
    project_event e
    JOIN project p ON p.id = e.project_id
    JOIN app_user u ON u.id = e.actor_id
ORDER BY
    e.id;
