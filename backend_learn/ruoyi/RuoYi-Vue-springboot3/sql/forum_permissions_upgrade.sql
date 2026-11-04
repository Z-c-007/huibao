-- 已导入过forum_demo.sql的本地数据库：在DBeaver用管理员账号执行整个脚本（Alt+X）。
-- 只新增本Demo的权限配置，不清空评论、不修改密码。完成后退出并重新登录以刷新权限。
USE `ry-vue`;
START TRANSACTION;
SET @forum_page = (SELECT menu_id FROM sys_menu WHERE perms='forum:topic:query' AND remark='forum-demo-v1');
INSERT INTO sys_menu (menu_name,parent_id,order_num,path,menu_type,visible,status,perms,create_by,create_time,remark)
SELECT p.label,@forum_page,p.seq,'#','F','0','0',p.perm,'forum-demo',NOW(),'forum-demo-v1'
FROM (
    SELECT '编辑评论' AS label,4 AS seq,'forum:comment:edit' AS perm
    UNION ALL SELECT '删除评论',5,'forum:comment:remove'
    UNION ALL SELECT '编辑自己的维护回复',6,'forum:reply:edit'
    UNION ALL SELECT '删除自己的维护回复',7,'forum:reply:remove'
) p
WHERE @forum_page IS NOT NULL AND NOT EXISTS (SELECT 1 FROM sys_menu m WHERE m.perms=p.perm);

INSERT INTO sys_role_menu (role_id,menu_id)
SELECT r.role_id,m.menu_id FROM sys_role r CROSS JOIN sys_menu m
WHERE r.role_key='forum_operator' AND r.remark='forum-demo-v1' AND m.remark='forum-demo-v1'
AND m.perms IN ('forum:comment:edit','forum:comment:remove','forum:reply:edit','forum:reply:remove')
AND NOT EXISTS (SELECT 1 FROM sys_role_menu rm WHERE rm.role_id=r.role_id AND rm.menu_id=m.menu_id);
COMMIT;

-- 预期4行，且role_key都是forum_operator；0行应检查原Demo是否已初始化。
SELECT r.role_key,m.perms FROM sys_role_menu rm
JOIN sys_role r ON r.role_id=rm.role_id JOIN sys_menu m ON m.menu_id=rm.menu_id
WHERE r.remark='forum-demo-v1' AND m.remark='forum-demo-v1'
AND m.perms IN ('forum:comment:edit','forum:comment:remove','forum:reply:edit','forum:reply:remove');
