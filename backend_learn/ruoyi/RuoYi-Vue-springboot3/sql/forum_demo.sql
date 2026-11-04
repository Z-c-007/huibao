-- 在后端实际使用的本地 ry-vue 数据库执行。仅新增本Demo对象，不重建若依系统表。
-- 两个非超级管理员账号：forum_member / forum_operator；初始密码见运行手册。
-- 密码字段为使用项目 BCryptPasswordEncoder 生成的哈希，重复执行不重置密码。
CREATE TABLE IF NOT EXISTS biz_forum_topic (
    topic_id BIGINT NOT NULL AUTO_INCREMENT,
    topic_key VARCHAR(64) NOT NULL COMMENT '预置主题业务键',
    title VARCHAR(100) NOT NULL,
    description VARCHAR(1000) NOT NULL,
    create_time DATETIME NOT NULL,
    PRIMARY KEY (topic_id), UNIQUE KEY uk_forum_topic_key (topic_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反馈讨论主题';

CREATE TABLE IF NOT EXISTS biz_forum_comment (
    comment_id BIGINT NOT NULL AUTO_INCREMENT,
    topic_id BIGINT NOT NULL,
    parent_id BIGINT DEFAULT NULL COMMENT 'NULL为顶层评论，非空为一级回复',
    author_id BIGINT NOT NULL,
    author_name VARCHAR(30) NOT NULL COMMENT '发表时昵称快照',
    content VARCHAR(200) NOT NULL,
    create_by VARCHAR(64) NOT NULL,
    create_time DATETIME NOT NULL,
    PRIMARY KEY (comment_id),
    KEY idx_forum_thread (topic_id, parent_id, comment_id),
    CONSTRAINT fk_forum_topic FOREIGN KEY (topic_id) REFERENCES biz_forum_topic(topic_id),
    CONSTRAINT fk_forum_parent FOREIGN KEY (parent_id) REFERENCES biz_forum_comment(comment_id),
    CONSTRAINT chk_forum_content CHECK (CHAR_LENGTH(TRIM(content)) BETWEEN 1 AND 200)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论与维护人员一级回复';

-- 检查同名账号、角色、路由是否由本Demo管理。冲突即停止，不能给已有账号意外授权。
DROP TEMPORARY TABLE IF EXISTS forum_seed_guard;
CREATE TEMPORARY TABLE forum_seed_guard (ok TINYINT NOT NULL CHECK (ok = 1));
INSERT INTO forum_seed_guard VALUES (
    NOT EXISTS (SELECT 1 FROM sys_user WHERE user_name IN ('forum_member','forum_operator') AND COALESCE(remark,'') <> 'forum-demo-v1')
    AND NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key IN ('forum_member','forum_operator') AND COALESCE(remark,'') <> 'forum-demo-v1')
    AND NOT EXISTS (SELECT 1 FROM sys_menu WHERE (perms LIKE 'forum:%' OR (parent_id=0 AND path='forum')) AND COALESCE(remark,'') <> 'forum-demo-v1')
);

START TRANSACTION;
INSERT INTO biz_forum_topic (topic_key,title,description,create_time)
SELECT 'valve-feedback','阀井台账系统使用反馈','请分享台账查询、现场巡检及系统使用中的建议。维护人员会在评论下回复。',NOW()
WHERE NOT EXISTS (SELECT 1 FROM biz_forum_topic WHERE topic_key='valve-feedback');

INSERT INTO sys_role (role_name,role_key,role_sort,data_scope,status,del_flag,create_by,create_time,remark)
SELECT '讨论区普通成员','forum_member',20,'5','0','0','forum-demo',NOW(),'forum-demo-v1'
WHERE NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key='forum_member');
INSERT INTO sys_role (role_name,role_key,role_sort,data_scope,status,del_flag,create_by,create_time,remark)
SELECT '讨论区维护人员','forum_operator',21,'5','0','0','forum-demo',NOW(),'forum-demo-v1'
WHERE NOT EXISTS (SELECT 1 FROM sys_role WHERE role_key='forum_operator');

-- 使用现有正常部门；未找到时不插入用户，最后的检查会失败并要求检查部门。
SET @forum_dept = (SELECT dept_id FROM sys_dept WHERE status='0' AND del_flag='0' ORDER BY dept_id LIMIT 1);
INSERT INTO sys_user (dept_id,user_name,nick_name,password,status,del_flag,pwd_update_date,create_by,create_time,remark)
SELECT @forum_dept,'forum_member','普通成员','$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.','0','0',NOW(),'forum-demo',NOW(),'forum-demo-v1'
WHERE @forum_dept IS NOT NULL AND NOT EXISTS (SELECT 1 FROM sys_user WHERE user_name='forum_member');
INSERT INTO sys_user (dept_id,user_name,nick_name,password,status,del_flag,pwd_update_date,create_by,create_time,remark)
SELECT @forum_dept,'forum_operator','业务维护人员','$2a$10$e0FPZPPr0tj/pLADCCWLZu/bVhFkShVB.OwxuB9m85ycMVM0nCVg.','0','0',NOW(),'forum-demo',NOW(),'forum-demo-v1'
WHERE @forum_dept IS NOT NULL AND NOT EXISTS (SELECT 1 FROM sys_user WHERE user_name='forum_operator');
INSERT INTO forum_seed_guard VALUES (@forum_dept IS NOT NULL);

INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time,remark)
SELECT '反馈讨论',0,8,'forum',NULL,1,1,'M','0','0','','message','forum-demo',NOW(),'forum-demo-v1'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE parent_id=0 AND path='forum');
SET @forum_root = (SELECT menu_id FROM sys_menu WHERE parent_id=0 AND path='forum' AND remark='forum-demo-v1');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,component,is_frame,is_cache,menu_type,visible,status,perms,icon,create_by,create_time,remark)
SELECT '讨论区',@forum_root,1,'discussion','forum/discussion/index',1,1,'C','0','0','forum:topic:query','message','forum-demo',NOW(),'forum-demo-v1'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='forum:topic:query');
SET @forum_page = (SELECT menu_id FROM sys_menu WHERE perms='forum:topic:query' AND remark='forum-demo-v1');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,menu_type,visible,status,perms,create_by,create_time,remark)
SELECT '查询讨论',@forum_page,1,'#','F','0','0','forum:comment:list','forum-demo',NOW(),'forum-demo-v1'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='forum:comment:list');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,menu_type,visible,status,perms,create_by,create_time,remark)
SELECT '发表评论',@forum_page,2,'#','F','0','0','forum:comment:add','forum-demo',NOW(),'forum-demo-v1'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='forum:comment:add');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,menu_type,visible,status,perms,create_by,create_time,remark)
SELECT '维护人员回复',@forum_page,3,'#','F','0','0','forum:reply:add','forum-demo',NOW(),'forum-demo-v1'
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE perms='forum:reply:add');

-- 编辑/删除仅分配给维护人员；重复初始化不会把这些权限授予普通成员。
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,menu_type,visible,status,perms,create_by,create_time,remark)
SELECT p.label,@forum_page,p.seq,'#','F','0','0',p.perm,'forum-demo',NOW(),'forum-demo-v1'
FROM (
    SELECT '编辑评论' AS label,4 AS seq,'forum:comment:edit' AS perm
    UNION ALL SELECT '删除评论',5,'forum:comment:remove'
    UNION ALL SELECT '编辑自己的维护回复',6,'forum:reply:edit'
    UNION ALL SELECT '删除自己的维护回复',7,'forum:reply:remove'
) p
WHERE NOT EXISTS (SELECT 1 FROM sys_menu m WHERE m.perms=p.perm);

INSERT INTO sys_user_role (user_id,role_id)
SELECT u.user_id,r.role_id FROM sys_user u JOIN sys_role r ON u.user_name=r.role_key
WHERE u.user_name IN ('forum_member','forum_operator') AND u.remark='forum-demo-v1' AND r.remark='forum-demo-v1'
AND NOT EXISTS (SELECT 1 FROM sys_user_role ur WHERE ur.user_id=u.user_id AND ur.role_id=r.role_id);
INSERT INTO sys_role_menu (role_id,menu_id)
SELECT r.role_id,m.menu_id FROM sys_role r CROSS JOIN sys_menu m
WHERE r.role_key IN ('forum_member','forum_operator') AND r.remark='forum-demo-v1' AND m.remark='forum-demo-v1'
AND (r.role_key='forum_operator' OR COALESCE(m.perms,'') IN ('','forum:topic:query','forum:comment:list','forum:comment:add'))
AND NOT EXISTS (SELECT 1 FROM sys_role_menu rm WHERE rm.role_id=r.role_id AND rm.menu_id=m.menu_id);
COMMIT;
DROP TEMPORARY TABLE forum_seed_guard;
SELECT '论坛初始化完成；重复执行不会清空评论或重置账号密码' AS result;
