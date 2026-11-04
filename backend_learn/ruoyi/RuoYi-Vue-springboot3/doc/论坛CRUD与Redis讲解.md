# 论坛编辑、删除与 Redis 登录流程

## 本次验证范围（2026-10-28）

后端Maven构建通过，21项业务/方法权限测试全部通过。隔离浏览器的普通成员、维护人员两种角色交互测试通过，包括编辑、删除、确认提示和移动端布局；这些测试使用测试接口数据，不代表真实MySQL联调。未自动执行权限升级SQL，也未修改运行中的后端进程；需按下述步骤启用并验证真实账号效果。

## 启用本次功能

1. 在 DBeaver 打开 `sql/forum_permissions_upgrade.sql`，确认连接本地 `ry-vue`，使用管理员账号按 Alt+X 执行整个脚本。
2. 最后的查询预期返回4条权限，所属角色都是 `forum_operator`。此脚本不改表结构，不清空评论，不改密码。
3. IDEA 停止并重新启动后端。前端仍在 `D:\GIS_learn\backend_learn\ruoyi\RuoYi-Vue3` 使用 `npm.cmd run dev`。
4. 退出账号后重新登录。手工SQL变更不会自动更新已缓存的登录权限，必须重新登录取得新权限。
5. 使用普通成员确认看不到编辑/删除；使用维护人员确认看到编辑评论、删除评论，以及自己的回复下的编辑/删除。

权限矩阵：普通成员只有查看、新增评论；维护人员可新增评论、回复，编辑/删除顶层评论，编辑/删除自己的回复。即使直接构造请求，后端权限和所有权检查仍然有效。删除顶层评论会一并删除全部维护回复（包括其他维护人员的回复），页面会明确确认。

## 接口与调用链

|操作|接口|权限|
|---|---|---|
|编辑顶层评论|PUT /forum/comments/{commentId}|forum:comment:edit|
|删除顶层评论和其全部回复|DELETE /forum/comments/{commentId}|forum:comment:remove|
|编辑自己的回复|PUT /forum/replies/{commentId}|forum:reply:edit|
|删除自己的回复|DELETE /forum/replies/{commentId}|forum:reply:remove|

编辑请求体：`{"topicId":1,"content":"修改后的文字"}`。路径编号是待编辑/删除记录自己的commentId，例：原评论3、回复4。编辑返回AjaxResult.data，删除返回成功消息。仅改内容，作者、创建时间、父评论不会被客户端改写；本次不扩展数据库的修改时间字段。

页面 index.vue → API discussion.js → ForumController → IForumService → ForumServiceImpl.updateComment/deleteComment → ForumMapper → ForumMapper.xml → MySQL。新接口使用 @Log 记录操作日志。删除原评论的两条DELETE置于 @Transactional 事务中，先删除回复以满足自引用外键，再删除原评论；新增回复也在事务中锁定原评论，避免与删除过程交错。

## Redis：当前项目里的具体用途

Redis是提供键值等数据结构的存储服务。本项目用它保存有过期时间的登录信息；评论业务数据仍保存在MySQL。Windows当前使用的Memurai提供Redis兼容服务。

登录阶段：

1. SysLoginService完成认证；UserDetailsServiceImpl组装LoginUser，其中权限来自SysPermissionService.getMenuPermission。
2. TokenService.createToken(LoginUser)生成随机uuid，放入loginUser.token。
3. refreshToken把LoginUser写入Redis：键是`login_tokens:<uuid>`，值是登录对象，并设置过期时间。示例uuid是abc时，键就是`login_tokens:abc`。
4. createToken把uuid等声明写进签名JWT，返回浏览器。JWT不是整个LoginUser对象，也不把明文密码放入返回凭证。

后续请求阶段：

1. 浏览器统一request工具发送Authorization: Bearer <token>。
2. JwtAuthenticationTokenFilter调用TokenService.getLoginUser(request)。
3. TokenService从请求头取出token，解析并校验签名，取得uuid。
4. 用`login_tokens:<uuid>`读取Redis中的LoginUser；缓存不存在时不能仅凭JWT恢复成已登录用户。
5. 过滤器按有效期策略刷新缓存，并把LoginUser放入Authentication，再放入SecurityContextHolder。
6. @PreAuthorize调用PermissionService.hasPermi，读取上下文中的用户权限集合，判断能否执行操作。
7. save内的SecurityUtils.getLoginUser也从这个安全上下文读取身份，填入作者字段；它本身不会再次访问Redis。

两个同名方法区别：TokenService.getLoginUser(request)处理token并访问Redis；SecurityUtils.getLoginUser()从当前认证上下文读取已经识别的用户。前者是请求认证，后者是在权限/业务代码里使用身份。

一句汇报用表达：我使用若依原有的JWT与Redis登录机制，JWT携带登录标识，Redis保存带有效期的登录信息；过滤器识别用户并设置安全上下文，接口再校验权限，业务代码从上下文取得真实作者。

## 在DBeaver对照SQL

以下是学习示例，不会自动执行。直接操作SQL不会经过HTTP权限校验或记录Controller的操作日志，也不会刷新页面。真实编号以本地数据为准。修改和删除示例使用ROLLBACK便于观察，确认要保留时才改为COMMIT。

```sql
-- 查看顶层评论
SELECT * FROM `ry-vue`.biz_forum_comment
WHERE topic_id=1 AND parent_id IS NULL ORDER BY comment_id DESC LIMIT 10 OFFSET 0;

-- 查看评论3下面的回复（回复自己的编号可能是4）
SELECT * FROM `ry-vue`.biz_forum_comment
WHERE topic_id=1 AND parent_id=3 ORDER BY comment_id ASC LIMIT 10 OFFSET 0;

-- 新增评论：实际应用中的作者和时间由后端决定，下面作者101仅为示例。
START TRANSACTION;
INSERT INTO `ry-vue`.biz_forum_comment
(topic_id,parent_id,author_id,author_name,content,create_by,create_time)
VALUES (1,NULL,101,'业务维护人员','SQL新增评论演示','forum_operator',NOW());
SELECT LAST_INSERT_ID() AS new_comment_id;
ROLLBACK;

-- 新增对评论3的回复：原评论3必须存在且是主题1的顶层评论。
START TRANSACTION;
INSERT INTO `ry-vue`.biz_forum_comment
(topic_id,parent_id,author_id,author_name,content,create_by,create_time)
VALUES (1,3,101,'业务维护人员','SQL新增回复演示','forum_operator',NOW());
SELECT LAST_INSERT_ID() AS new_reply_id;
ROLLBACK;

-- 编辑自己的回复4，对应 PUT /forum/replies/4
START TRANSACTION;
UPDATE `ry-vue`.biz_forum_comment SET content='修改后的回复'
WHERE comment_id=4 AND topic_id=1 AND parent_id IS NOT NULL AND author_id=101;
SELECT * FROM `ry-vue`.biz_forum_comment WHERE comment_id=4;
ROLLBACK;

-- 编辑顶层评论3，对应 PUT /forum/comments/3
START TRANSACTION;
UPDATE `ry-vue`.biz_forum_comment SET content='修改后的原评论'
WHERE comment_id=3 AND topic_id=1 AND parent_id IS NULL;
SELECT * FROM `ry-vue`.biz_forum_comment WHERE comment_id=3;
ROLLBACK;

-- 只删除自己的回复4，对应 DELETE /forum/replies/4
START TRANSACTION;
DELETE FROM `ry-vue`.biz_forum_comment
WHERE comment_id=4 AND parent_id IS NOT NULL AND author_id=101;
SELECT * FROM `ry-vue`.biz_forum_comment WHERE comment_id=4;
ROLLBACK;

-- 删除顶层评论3和全部回复，对应 DELETE /forum/comments/3
-- 后端会先检查目标类型和权限，并与新增回复协同加锁。
START TRANSACTION;
SELECT * FROM `ry-vue`.biz_forum_comment WHERE comment_id=3 FOR UPDATE;
DELETE FROM `ry-vue`.biz_forum_comment WHERE parent_id=3;
DELETE FROM `ry-vue`.biz_forum_comment WHERE comment_id=3 AND parent_id IS NULL;
SELECT * FROM `ry-vue`.biz_forum_comment WHERE comment_id=3 OR parent_id=3;
ROLLBACK;
```

普通成员直接在DBeaver执行SQL不受前端角色限制：数据库账号权限与应用里的用户角色是两套机制。演示角色权限请通过页面/HTTP接口操作。
