-- 新数据库完整安装用；已有V1数据库仅执行upgrade_v1_to_v2.sql。
-- 新业务独立数据库；请使用具有CREATE DATABASE/CREATE USER权限的MySQL管理员执行。
CREATE DATABASE IF NOT EXISTS project_approval_demo CHARACTER SET utf8mb4;

USE project_approval_demo;

CREATE TABLE IF NOT EXISTS organization (
    id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id BIGINT NULL,
    FOREIGN KEY (parent_id) REFERENCES organization (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS app_user (
    id BIGINT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(50) NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    org_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (org_id) REFERENCES organization (id),
    CHECK (role IN ('REPORTER', 'REVIEWER'))
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS login_session (
    token_hash CHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES app_user (id),
    INDEX idx_session_user (user_id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS project (
    id CHAR(36) PRIMARY KEY,
    project_code VARCHAR(40) NOT NULL UNIQUE,
    project_name VARCHAR(100) NOT NULL,
    amount DECIMAL(14, 2) NOT NULL,
    material TEXT NOT NULL,
    creator_id BIGINT NOT NULL,
    org_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    round_no INT NOT NULL DEFAULT 0,
    version BIGINT NOT NULL DEFAULT 0,
    current_step_id CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES app_user (id),
    FOREIGN KEY (org_id) REFERENCES organization (id),
    INDEX idx_project_creator (creator_id, status, updated_at),
    CHECK (amount >= 0),
    CHECK (status IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED'))
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS approval_step (
    id CHAR(36) PRIMARY KEY,
    project_id CHAR(36) NOT NULL,
    round_no INT NOT NULL,
    seq INT NOT NULL,
    org_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    actor_id BIGINT NULL,
    opinion VARCHAR(1000) NULL,
    acted_at DATETIME NULL,
    UNIQUE KEY uk_step_round (project_id, round_no, seq),
    FOREIGN KEY (project_id) REFERENCES project (id),
    FOREIGN KEY (org_id) REFERENCES organization (id),
    FOREIGN KEY (actor_id) REFERENCES app_user (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS approval_assignee (
    step_id CHAR(36) NOT NULL,
    user_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    PRIMARY KEY (step_id, user_id),
    INDEX idx_assignee_user (user_id, status),
    FOREIGN KEY (step_id) REFERENCES approval_step (id),
    FOREIGN KEY (user_id) REFERENCES app_user (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS project_event (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id CHAR(36) NOT NULL,
    actor_id BIGINT NOT NULL,
    action VARCHAR(20) NOT NULL,
    note VARCHAR(1000) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES project (id),
    FOREIGN KEY (actor_id) REFERENCES app_user (id)
) ENGINE = InnoDB;

INSERT IGNORE INTO
    organization (id, name, parent_id)
VALUES
    (1, '集团', NULL),
    (2, '二级公司A', 1),
    (3, '三级公司B', 2),
    (4, '三级公司C', 2);

-- 演示初始密码均为ForumDemo2026!，保存BCrypt哈希，重复初始化不重置密码。
INSERT IGNORE INTO
    app_user (id, username, display_name, password_hash, org_id, role)
VALUES
    (
        101,
        'report_b',
        '张三·三级B填报人',
        '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
        3,
        'REPORTER'
    ),
    (
        102,
        'review_b1',
        '李四·三级B审批人',
        '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
        3,
        'REVIEWER'
    ),
    (
        103,
        'review_b2',
        '王五·三级B审批人',
        '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
        3,
        'REVIEWER'
    ),
    (
        104,
        'review_a1',
        '赵六·二级A审批人',
        '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
        2,
        'REVIEWER'
    ),
    (
        105,
        'review_a2',
        '钱七·二级A审批人',
        '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
        2,
        'REVIEWER'
    ),
    (
        106,
        'review_group',
        '集团审批人',
        '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
        1,
        'REVIEWER'
    ),
    (
        107,
        'report_c',
        '孙八·三级C填报人',
        '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
        4,
        'REPORTER'
    );

-- 专用后端连接账号，仅能读写新业务数据库，不授予建库或修改表结构的权限。
-- 这是本地演示初始密码，与网页登录密码不同。若在此修改，也需重新运行configure-local.ps1填写相同值。
-- 重复执行不重设已有数据库账号密码；不要把已有账号的密码改动混入初始化。
CREATE USER IF NOT EXISTS 'approval_app' @'localhost' IDENTIFIED BY 'ApprovalDb2026!';

GRANT
SELECT
,
INSERT
,
UPDATE,
DELETE ON project_approval_demo.* TO 'approval_app' @'localhost';

SELECT
    '独立项目审批业务表、账号与数据库连接权限初始化完成' AS result;

-- 在DBeaver使用MySQL管理员执行整份脚本（Alt+X），遇错停止。
-- 不清空旧数据；旧login_session不再使用，保留以便回看。
USE project_approval_demo;

CREATE TABLE IF NOT EXISTS app_schema_version (version VARCHAR(20) PRIMARY KEY, installed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS app_user_security (
    user_id BIGINT PRIMARY KEY,
    auth_version BIGINT NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES app_user (id)
) ENGINE = InnoDB COMMENT = '权限和密码变更版本';

CREATE TABLE IF NOT EXISTS app_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    built_in BOOLEAN NOT NULL DEFAULT FALSE
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS app_permission (code VARCHAR(80) PRIMARY KEY, name VARCHAR(100) NOT NULL, category VARCHAR(20) NOT NULL) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS app_user_role (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES app_user (id),
    FOREIGN KEY (role_id) REFERENCES app_role (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS app_role_permission (
    role_id BIGINT NOT NULL,
    permission_code VARCHAR(80) NOT NULL,
    PRIMARY KEY (role_id, permission_code),
    FOREIGN KEY (role_id) REFERENCES app_role (id),
    FOREIGN KEY (permission_code) REFERENCES app_permission (code)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS app_id_sequence (name VARCHAR(30) PRIMARY KEY, next_id BIGINT NOT NULL) ENGINE = InnoDB COMMENT = '兼容V1非自增用户主键，事务内加锁取号';

CREATE TABLE IF NOT EXISTS app_audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category VARCHAR(20) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    actor_id BIGINT NULL,
    actor_name VARCHAR(50) NULL,
    request_id VARCHAR(36) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    ip VARCHAR(64) NOT NULL,
    success BOOLEAN NOT NULL,
    http_status INT NOT NULL,
    duration_millis BIGINT NOT NULL,
    message VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_category (category, created_at),
    INDEX idx_audit_request (request_id)
) ENGINE = InnoDB COMMENT = '登录、业务和管理操作审计；不保存密码或Token';

CREATE TABLE IF NOT EXISTS project_submission (
    id CHAR(36) PRIMARY KEY,
    project_id CHAR(36) NOT NULL,
    round_no INT NOT NULL,
    submitter_id BIGINT NOT NULL,
    submitter_name VARCHAR(50) NULL,
    org_id BIGINT NULL,
    org_name VARCHAR(100) NULL,
    project_code VARCHAR(40) NULL,
    project_name VARCHAR(100) NULL,
    amount DECIMAL(14, 2) NULL,
    material TEXT NULL,
    status VARCHAR(20) NOT NULL,
    snapshot_available BOOLEAN NOT NULL,
    idempotency_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    request_hash CHAR(64) CHARACTER SET ascii NULL,
    submitted_at DATETIME NULL,
    closed_at DATETIME NULL,
    UNIQUE KEY uk_submission_round (project_id, round_no),
    UNIQUE KEY uk_submission_request (submitter_id, idempotency_key),
    FOREIGN KEY (project_id) REFERENCES project (id),
    FOREIGN KEY (submitter_id) REFERENCES app_user (id)
) ENGINE = InnoDB COMMENT = '提交快照、轮次和持久化幂等结果';

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project'
                AND column_name = 'deleted'
        ),
        'SELECT 1',
        'ALTER TABLE `project` ADD COLUMN `deleted` BOOLEAN NOT NULL DEFAULT FALSE'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'approval_step'
                AND column_name = 'started_at'
        ),
        'SELECT 1',
        'ALTER TABLE `approval_step` ADD COLUMN `started_at` DATETIME NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'approval_step'
                AND column_name = 'actor_name'
        ),
        'SELECT 1',
        'ALTER TABLE `approval_step` ADD COLUMN `actor_name` VARCHAR(50) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'approval_step'
                AND column_name = 'org_name'
        ),
        'SELECT 1',
        'ALTER TABLE `approval_step` ADD COLUMN `org_name` VARCHAR(100) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'approval_assignee'
                AND column_name = 'username'
        ),
        'SELECT 1',
        'ALTER TABLE `approval_assignee` ADD COLUMN `username` VARCHAR(50) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'approval_assignee'
                AND column_name = 'display_name'
        ),
        'SELECT 1',
        'ALTER TABLE `approval_assignee` ADD COLUMN `display_name` VARCHAR(50) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project_event'
                AND column_name = 'round_no'
        ),
        'SELECT 1',
        'ALTER TABLE `project_event` ADD COLUMN `round_no` INT NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project_event'
                AND column_name = 'step_id'
        ),
        'SELECT 1',
        'ALTER TABLE `project_event` ADD COLUMN `step_id` CHAR(36) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project_event'
                AND column_name = 'actor_name'
        ),
        'SELECT 1',
        'ALTER TABLE `project_event` ADD COLUMN `actor_name` VARCHAR(50) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project_event'
                AND column_name = 'before_status'
        ),
        'SELECT 1',
        'ALTER TABLE `project_event` ADD COLUMN `before_status` VARCHAR(20) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project_event'
                AND column_name = 'after_status'
        ),
        'SELECT 1',
        'ALTER TABLE `project_event` ADD COLUMN `after_status` VARCHAR(20) NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project_event'
                AND column_name = 'before_version'
        ),
        'SELECT 1',
        'ALTER TABLE `project_event` ADD COLUMN `before_version` BIGINT NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

SET
    @approval_ddl = IF(
        EXISTS (
            SELECT
                1
            FROM
                information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = 'project_event'
                AND column_name = 'after_version'
        ),
        'SELECT 1',
        'ALTER TABLE `project_event` ADD COLUMN `after_version` BIGINT NULL'
    );

PREPARE approval_stmt
FROM
    @approval_ddl;

EXECUTE approval_stmt;

DEALLOCATE PREPARE approval_stmt;

-- 新角色与权限。重复执行不覆盖管理员后来调整的权限。
INSERT IGNORE INTO
    app_role (id, code, name, built_in)
VALUES
    (1, 'REPORTER', '材料填报人', FALSE),
    (2, 'REVIEWER', '材料审批人', FALSE),
    (3, 'ADMINISTRATOR', '系统管理员', TRUE);

INSERT IGNORE INTO
    app_permission (code, name, category)
VALUES
    ('approval:report:list', '查看本人材料列表', 'REPORT'),
    ('approval:report:query', '查看本人材料详情', 'REPORT'),
    ('approval:report:add', '新增材料', 'REPORT'),
    ('approval:report:edit', '编辑本人材料', 'REPORT'),
    ('approval:report:delete', '删除未提交草稿', 'REPORT'),
    ('approval:report:submit', '提交材料审核', 'REPORT'),
    ('approval:report:withdraw', '撤回本人在审材料', 'REPORT'),
    ('approval:review:list', '查看审批待办与已办', 'REVIEW'),
    ('approval:review:query', '查看有资格的提交快照', 'REVIEW'),
    ('approval:review:audit', '办理当前审批节点', 'REVIEW'),
    ('system:user:list', '查看用户及组织', 'ADMIN'),
    ('system:user:create', '新增用户', 'ADMIN'),
    ('system:user:assign', '分配用户角色', 'ADMIN'),
    ('system:user:disable', '启停其他用户', 'ADMIN'),
    ('system:user:revoke', '使用户全部会话失效', 'ADMIN'),
    ('system:role:list', '查看角色及权限', 'ADMIN'),
    ('system:role:edit', '修改非内置角色权限', 'ADMIN'),
    ('system:audit:list', '查看操作及登录日志', 'ADMIN');

INSERT IGNORE INTO
    app_role_permission (role_id, permission_code)
SELECT
    1,
    code
FROM
    app_permission
WHERE
    category = 'REPORT'
    AND NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

INSERT IGNORE INTO
    app_role_permission (role_id, permission_code)
SELECT
    2,
    code
FROM
    app_permission
WHERE
    category = 'REVIEW'
    AND NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

INSERT IGNORE INTO
    app_role_permission (role_id, permission_code)
SELECT
    3,
    code
FROM
    app_permission
WHERE
    category = 'ADMIN'
    AND NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

-- 先转换V1角色，再让管理员通过关联表维护；旧app_user.role列仅保留兼容，不再用于鉴权。
INSERT IGNORE INTO
    app_user_role (user_id, role_id)
SELECT
    id,
    CASE
        WHEN role = 'REPORTER' THEN 1
        ELSE 2
    END
FROM
    app_user
WHERE
    username != 'admin'
    AND NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

SET
    @approval_admin_id = (
        SELECT
            GREATEST(COALESCE(MAX(id), 0) + 1, 900)
        FROM
            app_user
    );

INSERT IGNORE INTO
    app_user (id, username, display_name, password_hash, org_id, role, enabled)
SELECT
    @approval_admin_id,
    'admin',
    '系统管理员',
    '$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.',
    1,
    'REPORTER',
    TRUE
WHERE
    NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

INSERT IGNORE INTO
    app_user_role (user_id, role_id)
SELECT
    id,
    3
FROM
    app_user
WHERE
    username = 'admin'
    AND NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

INSERT IGNORE INTO
    app_user_security (user_id, auth_version)
SELECT
    id,
    0
FROM
    app_user;

INSERT IGNORE INTO
    app_id_sequence (name, next_id)
SELECT
    'USER',
    GREATEST(COALESCE(MAX(id), 0) + 1, 1000)
FROM
    app_user;

-- V1没有历史材料快照，不能把最新内容伪装成旧轮次内容。只补轮次标识，标记快照不可用。
INSERT IGNORE INTO
    project_submission (id, project_id, round_no, submitter_id, status, snapshot_available)
SELECT
    UUID(),
    p.id,
    r.round_no,
    p.creator_id,
    CASE
        WHEN EXISTS (
            SELECT
                1
            FROM
                approval_step n
            WHERE
                n.project_id = p.id
                AND n.round_no = r.round_no
                AND n.status = 'REJECTED'
        ) THEN 'REJECTED'
        WHEN r.round_no = p.round_no
        AND p.status = 'APPROVED' THEN 'APPROVED'
        WHEN r.round_no = p.round_no
        AND p.status = 'PENDING' THEN 'PENDING'
        ELSE 'CANCELLED'
    END,
    FALSE
FROM
    project p
    JOIN (
        SELECT DISTINCT
            project_id,
            round_no
        FROM
            approval_step
    ) r ON r.project_id = p.id
WHERE
    NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

UPDATE approval_step
SET
    started_at = COALESCE(acted_at, NOW())
WHERE
    started_at IS NULL
    AND status IN ('PENDING', 'PASSED', 'REJECTED')
    AND NOT EXISTS (
        SELECT
            1
        FROM
            app_schema_version
        WHERE
            version = '2'
    );

UPDATE approval_step n
JOIN organization o ON o.id = n.org_id
SET
    n.org_name = o.name
WHERE
    n.org_name IS NULL;

UPDATE approval_assignee a
JOIN app_user u ON u.id = a.user_id
SET
    a.username = u.username,
    a.display_name = u.display_name
WHERE
    a.username IS NULL;

INSERT IGNORE INTO
    app_schema_version (version)
VALUES
    ('2');

SELECT
    'V2升级完成。旧在审材料建议由填报人撤回再提交，以生成真实材料快照。' AS result;
