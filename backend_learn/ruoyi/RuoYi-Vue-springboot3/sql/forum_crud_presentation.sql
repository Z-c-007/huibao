-- ============================================================================
-- 论坛 Demo：汇报用 SQL（用户身份 / 角色权限 / 评论和回复的增删改查）
-- ============================================================================
-- 文件用途：对照 Java Controller → Service → Mapper → XML，演示真实数据库操作。
-- 这不是初始化脚本；需先完成 forum_demo.sql 和 forum_permissions_upgrade.sql。
--
-- DBeaver 使用方法：
-- 1. 打开本文件，连接本地 MySQL 的 ry-vue 数据库。
-- 2. 演示时选中一条完整 SQL（包括末尾分号），按 Ctrl+Enter 执行。
-- 3. 同时执行多条 SQL 时，使用“执行 SQL 脚本”（Alt+X），不要把多条当成一条执行。
-- 4. 始终使用同一个连接，@开头的变量只保存在当前数据库连接中。
-- 5. 先执行【01】【02】展示现有数据，再从【03】开始依次执行增删改查。
-- 6. INSERT 后紧接着执行记录编号的 SET，中间不要插入其他 SQL。
--
-- 重要概念：没有单独的“回复表”。评论、回复都在 biz_forum_comment 中：
-- parent_id IS NULL     → 顶层评论。
-- parent_id IS NOT NULL → 回复，parent_id 指向原评论自己的 comment_id。
-- 身份表 sys_user 属于 MySQL；Redis 中的 LoginUser 是登录缓存，不是下面这些表。
-- 直接执行 SQL 不经过若依的接口权限、作者归属检查及 Controller 操作日志。
-- 下方写操作仅针对本次 INSERT 新建的演示编号，不使用已有评论3、回复4作为删除目标。
-- 整个文件执行完后会删除本次演示评论和回复；不会清空已有评论。

USE `ry-vue`;


-- ============================================================================
-- 【01】查身份表：用户是谁？属于哪个角色？拥有哪些权限？（全部为只读查询）
-- ============================================================================

-- 01-1 用户身份表：查看论坛的两个用户。
-- user_id是用户编号，user_name是登录账号，nick_name是昵称。
-- status：0正常、1停用；del_flag：0存在、2删除。
-- 不选择password字段，汇报无需展示密码哈希。
SELECT user_id, user_name, nick_name, dept_id, status, del_flag
FROM sys_user
WHERE user_name IN ('forum_member', 'forum_operator')
ORDER BY user_id;

-- 01-2 若想查看全部未删除用户，使用这一条，而不是论坛账号过滤条件。
SELECT user_id, user_name, nick_name, dept_id, status
FROM sys_user
WHERE del_flag = '0'
ORDER BY user_id;

-- 01-3 角色表：角色名称和角色标识。
SELECT role_id, role_name, role_key, status
FROM sys_role
WHERE role_key IN ('forum_member', 'forum_operator')
ORDER BY role_id;

-- 01-4 用户 → 用户角色关联表 → 角色：确认每个账号实际分配的角色。
SELECT u.user_id, u.user_name, u.nick_name,
       r.role_id, r.role_name, r.role_key
FROM sys_user u
JOIN sys_user_role ur ON ur.user_id = u.user_id
JOIN sys_role r ON r.role_id = ur.role_id
WHERE u.user_name IN ('forum_member', 'forum_operator')
  AND u.del_flag = '0' AND r.del_flag = '0'
ORDER BY u.user_name, r.role_id;

-- 01-5 用户 → 角色 → 菜单/按钮权限：查看接口权限标识的数据库配置来源。
-- perms可以看到forum:comment:add、forum:reply:add、forum:comment:edit等。
-- 普通成员应只有查看、新增评论；维护人员额外拥有回复、编辑、删除相关权限。
-- 本查询展示当前数据库配置；程序会结合用户/角色状态等规则生成登录权限。
SELECT DISTINCT u.user_name, r.role_name, r.role_key,
                m.menu_name, m.perms
FROM sys_user u
JOIN sys_user_role ur ON ur.user_id = u.user_id
JOIN sys_role r ON r.role_id = ur.role_id
JOIN sys_role_menu rm ON rm.role_id = r.role_id
JOIN sys_menu m ON m.menu_id = rm.menu_id
WHERE u.user_name IN ('forum_member', 'forum_operator')
  AND u.del_flag = '0' AND r.del_flag = '0'
  AND m.perms LIKE 'forum:%'
ORDER BY u.user_name, m.perms;


-- ============================================================================
-- 【02】查全部业务数据：主题、全部评论和回复、只看评论、只看回复
-- ============================================================================

-- 02-1 查询全部主题。
SELECT topic_id, topic_key, title, description, create_time
FROM biz_forum_topic
ORDER BY topic_id;

-- 02-2 查询整个评论/回复表的全部记录（不按主题、不分页）。
-- 这一条就能看到所有顶层评论和所有回复。
SELECT *
FROM biz_forum_comment
ORDER BY comment_id;

-- 02-3 同样查询全部记录，但增加“记录类型”便于汇报展示。
SELECT comment_id, topic_id,
       CASE WHEN parent_id IS NULL THEN '顶层评论' ELSE '维护回复' END AS 记录类型,
       parent_id, author_id, author_name, content, create_by, create_time
FROM biz_forum_comment
ORDER BY comment_id;

-- 02-4 只查询全部顶层评论，不包含回复。
SELECT *
FROM biz_forum_comment
WHERE parent_id IS NULL
ORDER BY comment_id DESC;

-- 02-5 只查询全部回复，不包含顶层评论。
SELECT *
FROM biz_forum_comment
WHERE parent_id IS NOT NULL
ORDER BY parent_id, comment_id;

-- 02-6 用表的自关联把“回复”与“它回复的原评论”放到同一行展示。
-- 同一张表取两个别名reply、parent，分别代表回复记录和原评论记录。
SELECT reply.comment_id AS 回复编号,
       reply.author_name AS 回复作者,
       reply.content AS 回复内容,
       parent.comment_id AS 原评论编号,
       parent.author_name AS 原评论作者,
       parent.content AS 原评论内容
FROM biz_forum_comment reply
JOIN biz_forum_comment parent ON parent.comment_id = reply.parent_id
ORDER BY parent.comment_id, reply.comment_id;


-- ============================================================================
-- 【03】准备增删改查的示例变量：以下编号全部从真实数据取得
-- ============================================================================
-- @变量类似程序变量；例如@demo_comment_id记住刚新增的原评论编号。
SET @demo_comment_id = NULL;
SET @demo_reply_id = NULL;

SET @topic_id = (
    SELECT topic_id FROM biz_forum_topic WHERE topic_key = 'valve-feedback'
);
SET @member_id = (
    SELECT user_id FROM sys_user WHERE user_name = 'forum_member' AND del_flag = '0'
);
SET @operator_id = (
    SELECT user_id FROM sys_user WHERE user_name = 'forum_operator' AND del_flag = '0'
);

-- 这3个值应当都有数值；若为NULL，先检查初始化数据，不继续执行写操作。
SELECT @topic_id AS 主题编号,
       @member_id AS 填报人员编号,
       @operator_id AS 维护人员编号;


-- ============================================================================
-- 【04】评论的“增”：INSERT —— 对应 POST /forum/comments
-- ============================================================================
-- 从真实用户表取得作者资料；parent_id=NULL，表示这是一条顶层评论。
-- 正常情况下插入1条；主题/用户不存在时不插入，防止生成无效演示记录。
INSERT INTO biz_forum_comment (
    topic_id, parent_id, author_id, author_name, content, create_by, create_time
)
SELECT @topic_id, NULL, u.user_id, u.nick_name,
       '演示评论：建议增加按阀井编号搜索的功能。', u.user_name, NOW()
FROM sys_user u
WHERE u.user_id = @member_id
  AND EXISTS (SELECT 1 FROM biz_forum_topic WHERE topic_id = @topic_id);

-- 紧接着执行：若刚才成功插入1条，记住新主键；否则置NULL，不使用旧的自增编号。
SET @demo_comment_id = IF(ROW_COUNT() = 1, LAST_INSERT_ID(), NULL);
SELECT @demo_comment_id AS 新增评论编号;


-- ============================================================================
-- 【05】评论的“查”：SELECT —— 对应 GET /forum/comments
-- ============================================================================
-- 查询当前主题的顶层评论，第1页，每页10条。
SELECT comment_id, topic_id, parent_id, author_name, content, create_time
FROM biz_forum_comment
WHERE topic_id = @topic_id AND parent_id IS NULL
ORDER BY comment_id DESC
LIMIT 10 OFFSET 0;

-- 分页接口total对应的总条数，不受LIMIT限制。
SELECT COUNT(*) AS total
FROM biz_forum_comment
WHERE topic_id = @topic_id AND parent_id IS NULL;

-- 只查看本次新增的演示评论。
SELECT * FROM biz_forum_comment WHERE comment_id = @demo_comment_id;


-- ============================================================================
-- 【06】评论的“改”：UPDATE —— 对应 PUT /forum/comments/{commentId}
-- ============================================================================
-- SET只修改文字；WHERE只定位本次演示的顶层评论。
UPDATE biz_forum_comment
SET content = '演示评论已修改：建议同时支持阀井编号和名称搜索。'
WHERE comment_id = @demo_comment_id AND parent_id IS NULL;

SELECT comment_id, author_name, content, create_time
FROM biz_forum_comment WHERE comment_id = @demo_comment_id;


-- ============================================================================
-- 【07】回复的“增”：INSERT —— 对应 POST /forum/replies
-- ============================================================================
-- parent_id使用原评论编号；新回复还会生成自己独立的comment_id。
INSERT INTO biz_forum_comment (
    topic_id, parent_id, author_id, author_name, content, create_by, create_time
)
SELECT @topic_id, @demo_comment_id, u.user_id, u.nick_name,
       '演示回复：建议已收到，我们会评估搜索功能。', u.user_name, NOW()
FROM sys_user u
JOIN biz_forum_comment parent ON parent.comment_id = @demo_comment_id
WHERE u.user_id = @operator_id
  AND parent.topic_id = @topic_id
  AND parent.parent_id IS NULL;

-- 紧接着执行，记住回复自己的编号。
SET @demo_reply_id = IF(ROW_COUNT() = 1, LAST_INSERT_ID(), NULL);
SELECT @demo_comment_id AS 原评论编号, @demo_reply_id AS 新回复编号;


-- ============================================================================
-- 【08】回复的“查”：SELECT —— 对应 GET /forum/comments/{原评论编号}/replies
-- ============================================================================
-- 按parent_id查原评论下面的回复，而不是拿回复编号去查parent_id。
SELECT comment_id, topic_id, parent_id, author_name, content, create_time
FROM biz_forum_comment
WHERE topic_id = @topic_id AND parent_id = @demo_comment_id
ORDER BY comment_id ASC
LIMIT 10 OFFSET 0;

SELECT COUNT(*) AS total
FROM biz_forum_comment
WHERE topic_id = @topic_id AND parent_id = @demo_comment_id;


-- ============================================================================
-- 【09】回复的“改”：UPDATE —— 对应 PUT /forum/replies/{回复自己的编号}
-- ============================================================================
-- author_id条件演示“只操作自己的回复”；HTTP接口还会检查对应操作权限。
UPDATE biz_forum_comment
SET content = '演示回复已修改：已安排评估，感谢反馈。'
WHERE comment_id = @demo_reply_id
  AND parent_id IS NOT NULL
  AND author_id = @operator_id;

SELECT comment_id, parent_id, author_name, content
FROM biz_forum_comment WHERE comment_id = @demo_reply_id;


-- ============================================================================
-- 【10】回复的“删”：DELETE —— 对应 DELETE /forum/replies/{回复自己的编号}
-- ============================================================================
-- 若想展示【11】“删除原评论时连同回复一起删除”，可跳过本节，直接执行【11】。
DELETE FROM biz_forum_comment
WHERE comment_id = @demo_reply_id
  AND parent_id IS NOT NULL
  AND author_id = @operator_id;

-- 回复应查不到；原评论应仍存在，说明删除回复不删除原评论。
SELECT * FROM biz_forum_comment WHERE comment_id = @demo_reply_id;
SELECT * FROM biz_forum_comment WHERE comment_id = @demo_comment_id;


-- ============================================================================
-- 【11】评论的“删”：DELETE —— 对应 DELETE /forum/comments/{原评论编号}
-- ============================================================================
-- 由于存在自引用外键，必须先删回复，再删原评论。
-- 把本节从START TRANSACTION到COMMIT作为一组演示；有错误则执行ROLLBACK，不要继续COMMIT。
START TRANSACTION;

-- 查询并锁定本次演示原评论；事务结束时释放锁。
SELECT * FROM biz_forum_comment
WHERE comment_id = @demo_comment_id AND parent_id IS NULL
FOR UPDATE;

-- 删除该原评论下面的全部回复。
DELETE FROM biz_forum_comment WHERE parent_id = @demo_comment_id;

-- 删除原评论自己。
DELETE FROM biz_forum_comment
WHERE comment_id = @demo_comment_id AND parent_id IS NULL;

COMMIT;

-- 原评论及其全部回复都应查不到，本次演示数据清理完成。
SELECT * FROM biz_forum_comment
WHERE comment_id = @demo_comment_id OR parent_id = @demo_comment_id;

-- 想重新展示数据库中所有实际记录，执行【02-2】或【02-3】即可。
