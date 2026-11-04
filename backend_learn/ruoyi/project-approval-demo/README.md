# 项目填报与审批：Java 分层实现 V2

本项目在原 `project-approval-demo` 上升级，由自己的 Java 代码实现安全与业务流程，参考若依的设计，不复制若依工程或工具封装。运行时只需 Java、MySQL、Redis/Memurai 和前端 Node 环境；不需要 Python。

原 `ruoyi-approval` 目录保持原样；原若依论坛与 `ry-vue` 数据库不参与此项目。

## 1. 已有数据库先做增量升级

你已经运行过V1，**只需在DBeaver使用MySQL管理员执行 `sql/upgrade_v1_to_v2.sql`**。整个脚本用“执行SQL脚本”（Alt+X），遇错停止，不把多条语句作为一条SQL发送。

- 仍使用 `project_approval_demo`，不需要新建数据库。
- 不删除原用户、材料、审批记录或修改已有密码。
- 新增角色权限、安全版本、审计和提交快照表；对原表只增加字段。
- 脚本通过元数据检查新增字段，可重复执行；完成后写入 `app_schema_version` 的版本2标记。
- `sql/init.sql` 是全新数据库的完整初始化文件；已有库不要用它替代增量升级。
- 旧在审材料没有真实提交快照，升级后请填报人“撤回”并重新提交。旧审批轨迹保留，不能把最新材料假装成历史快照。

完成后自行检查：

```sql
SELECT * FROM project_approval_demo.app_schema_version;
SELECT u.username,r.code,r.name
FROM project_approval_demo.app_user u
JOIN project_approval_demo.app_user_role ur ON ur.user_id=u.id
JOIN project_approval_demo.app_role r ON r.id=ur.role_id
ORDER BY u.id,r.id;
```

## 2. IDEA 启动后端

打开 `backend/pom.xml`，加载Maven，使用JDK17。

启动文件仍然是：

`backend/src/main/java/com/learning/approval/ApprovalApplication.java`

IDEA运行配置的工作目录设为本项目的backend目录。本机练习的MySQL账号、密码及Redis密码已直接写在backend/src/main/resources/application.yml中，不需要设置连接密码环境变量。

MySQL连接账号仍是 `approval_app`，库仍为 `project_approval_demo`，密码沿用IDEA原先已经连接成功的值。Redis密码与本机Memurai配置保持一致。

安全配置使用环境变量：

| 环境变量 | 用途 | 本机默认 |
| --- | --- | --- |
| APP_PROFILE | 配置环境 | local |
| APP_JWT_SECRET | 至少64随机字节的Base64密钥 | local配置提供独立的本机学习值 |
| APP_LOG_FILE | 文件日志位置 | logs/approval.log，相对于工作目录 |

数据库和Redis连接直接修改application.yml中的spring.datasource及spring.data.redis。上表保留的是其他可选环境配置；本机默认local配置无需切换到prod。

升级后先在IDEA选择“构建 → 重新构建项目”，清除旧版本遗留的class文件，再启动。

Memurai必须处于运行状态。本项目默认用Redis第6号逻辑库和 `approval:v2:` 前缀，不需要清空原项目的Redis数据。

启动时会只读检查V2数据库结构和Redis连接；日志出现“依赖检查完成”并且进程持续运行后再访问。启动过程不执行建表、迁移或业务写入。

后端仍为 `http://127.0.0.1:8081`。默认只监听本机。

## 3. 前端启动

```powershell
cd D:\GIS_learn\backend_learn\ruoyi\project-approval-demo\frontend
npm run dev
```

打开 `http://127.0.0.1:5174`。依赖仍为Vue3/Vite，没有为了模拟若依而引入另一套后台框架。

V1随机Token与V2 JWT不兼容，升级后重新登录。

## 4. 账号和业务角色

**演示初始网页登录密码均为 `ForumDemo2026!`；已有账号如果自己改过密码，仍使用修改后的值。**

| 账号 | 所属组织 | 初始角色 |
| --- | --- | --- |
| report_b | 三级公司B | 材料填报人 |
| review_b1、review_b2 | 三级公司B | 材料审批人 |
| review_a1、review_a2 | 二级公司A | 材料审批人 |
| review_group | 集团 | 材料审批人 |
| report_c | 三级公司C | 材料填报人 |
| admin | 集团 | 系统管理员（V2新增） |

管理员默认只具有系统管理权限，不默认审核业务材料。需要时可以给其他管理账号分配业务角色。一个用户可有多个角色。

权限真正来自 `app_user_role` 和 `app_role_permission`。旧 `app_user.role` 列仅为V1兼容而保留，不参与V2认证或授权。旧 `login_session` 表也保留，但V2会话只存Redis。

## 5. 可以看到的功能

- JWT签名校验、Redis会话、30分钟空闲有效期、临近10分钟续期、8小时JWT绝对上限。
- 连续5次登录失败暂时锁定10分钟；每个直连IP每分钟最多30次登录请求。
- 填报、审核页面及操作按钮按实际权限显示，后端通过Spring Security再次校验。
- 本人草稿保存、编辑、删除；提交、多人或签、逐级上报、驳回重提。
- 未选本级审批人时跳过本级向上找；父级无有效人员则继续向上；全路径无人时拒绝提交。
- 候选人必须拥有审核权限、账号与角色有效、属于目标组织，且不能是填报人本人。
- 审核中的本人材料可以撤回。原轮次取消并保留历史，回到草稿后可以修改重提。
- 每轮保存材料、组织、作者和候选人快照；旧审批人只能看自己被分配且实际激活过的轮次。
- 数据库行锁、版本校验、事务回滚、提交幂等，保护并发编辑和多人同时审批。
- 管理员新增用户、分配角色、启停用户、撤销会话、调整非内置角色权限、查看登录与操作日志。
- 修改密码和权限会更新数据库权限版本，旧凭证在下一次请求被拒绝；Redis清理在事务提交后进行。
- “个人安全与会话”可查看真实会话TTL、退出设备和查看JWT声明（仅解码，验签由后端完成）。

材料暂为文本说明；文件上传、导入导出、任意流程设计、转办委派不在本轮范围。固定流程由自己的Java状态流转代码实现，没有引入Flowable。

## 6. 如何开始读代码

先看 `docs/ARCHITECTURE.md` 的目录和链路，再逐个文件学习：

1. `controller/AuthController.java` → `service/IAuthService.java` → `service/impl/AuthServiceImpl.java`。
2. `mapper/UserMapper.java`、`mapper/RoleMapper.java` → 对应 `resources/mapper/*.xml`。
3. `security/JwtTokenProvider.java` → `RedisSessionService.java` → `JwtAuthenticationFilter.java` → `config/SecurityConfig.java`。
4. `controller/ProjectController.java` → `IProjectService.java` → `ProjectServiceImpl.java`。
5. `OrganizationApprovalRoutePlanner.java` → `ProjectMapper.xml`、`WorkflowMapper.xml`。
6. `audit/AuditAspect.java` → `AuditLogService.java` → `AuditMapper.xml`。

上述Java路径均位于 `backend/src/main/java/com/learning/approval`。

## 7. 日志与调试

IDEA控制台与日志文件都可查看。IDEA工作目录为backend时，默认日志文件是 `backend/logs/approval.log`。已有程序实参中的 `--logging.file.name=...` 仍会覆盖默认位置。

每个响应带 `requestId` 和 `X-Request-Id`。遇到错误，用它搜索文件日志或管理员审计日志。业务错误返回明确的400/401/403/409，依赖服务不可用返回503；不把SQL异常详情直接返回浏览器。

Redis查看示例（在Memurai CLI内执行；若有密码先完成AUTH）：

```text
SELECT 6
SCAN 0 MATCH approval:v2:session:* COUNT 100
TTL approval:v2:session:这里填写真实的jti
GET approval:v2:session:这里填写真实的jti
```

JWT里的 `jti`、页面会话ID和上述Redis键后缀一致。退出后会话键被删除，即使JWT的exp尚未到期也会被拒绝。

如需在控制台看业务SQL，可仅将 `com.learning.approval.mapper.ProjectMapper` 和 `WorkflowMapper` 的日志级别设为DEBUG。不要对登录/密码数据映射器开启参数日志。

## 8. 验收与边界

数据库导入、启动、真实账号登录和业务验收由你操作，详见 `docs/MANUAL_ACCEPTANCE.md`。编译通过只能说明源码与依赖能构建，不等于已通过数据库联调、并发或安全验收。

`APP_PROFILE=prod`时必须显式提供数据库密码和独立随机JWT密钥。上线还需按实际部署完成HTTPS、凭据管理、备份恢复、权限配置和验收，不把本机开发密钥用于部署。

原V1文件备份位于被Git忽略的 `.backup-v1`，其中可能包含你的本地配置，不要提交或分享该目录。
