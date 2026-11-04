# 源码架构与学习路线

## 分层职责

```text
com.learning.approval
├── ApprovalApplication.java       唯一main入口
├── config                        Security、参数、只读依赖检查
├── controller                    HTTP路由、参数校验、功能权限、返回对象
├── dto/request                   客户端允许提交的字段
├── dto/response                  明确的返回结构
├── service                       业务接口
│   └── impl                      Java业务实现与事务边界
├── security                      JWT、Redis会话、认证过滤器、权限失效
├── mapper                        MyBatis数据访问接口
├── domain                        数据库实体与查询模型
├── audit                         操作日志注解及AOP
├── exception                     统一异常处理
└── common                        响应、分页、摘要等小型公共功能

resources/mapper/*.xml            参数绑定SQL
```

Controller不写SQL、不操作Redis。业务Service不解析JWT。Mapper/XML负责持久化。JWT和Redis逻辑集中在security中。前端同样拆分为api、stores、views、components、composables。

## 自己实现与框架职责

| 部分 | 本项目自己的代码 | 基础库负责什么 |
| --- | --- | --- |
| HTTP | Controller、请求和响应对象 | Spring MVC路由、绑定、JSON序列化 |
| 认证 | 登录流程、JwtAuthenticationFilter | Spring Security过滤链与安全上下文 |
| JWT | JwtTokenProvider组织声明和校验规则 | JJWT计算/验证签名及检查exp |
| 会话 | RedisSessionService、LoginAttemptService | Spring Data Redis连接与命令执行 |
| 授权 | 权限表与@PreAuthorize配置 | Spring Security执行方法权限判断 |
| 业务 | ProjectServiceImpl、路径规划器 | Spring事务管理 |
| SQL | Mapper接口及XML | MyBatis绑定参数、映射结果、使用事务连接 |

不自己发明密码算法、Redis协议或JWT签名算法。自己的Java代码负责把这些能力组织成完整、可追踪的应用逻辑。

## 登录：以report_b为例

```text
POST /api/auth/login
→ AuthController接收LoginRequest
→ AuthServiceImpl检查Redis登录频率/失败计数
→ UserMapper.xml查询账号和BCrypt哈希
→ PasswordEncoder.matches校验
→ RoleMapper.xml查角色及权限字符串
→ 创建CurrentUser，不含密码
→ RedisSessionService保存LoginSession，TTL为30分钟
→ JwtTokenProvider签发HS512 JWT
→ 返回JWT与当前用户
```

JWT的主要声明：iss为项目标识，sub为用户ID，jti为随机会话ID，authVersion为身份版本，iat/exp为签发/最长到期时间。角色权限存在Redis会话中，JWT不承载完整权限集合。

## 携带JWT访问接口

```text
Authorization: Bearer JWT
→ RequestTraceFilter生成requestId
→ JwtAuthenticationFilter校验签名、issuer、exp
→ 用jti读取Redis会话
→ 对照会话中的用户ID、authVersion
→ UserMapper查询轻量SecurityStamp，检查停用/组织/权限版本
→ 临近过期时续Redis TTL，但不超过JWT绝对上限
→ 将CurrentUser和权限放入SecurityContext
→ @PreAuthorize检查功能权限
→ Controller通过@AuthenticationPrincipal获取CurrentUser
→ Service检查业务数据权限与流程状态
```

数据库的authVersion轻量检查是一项明确取舍：每次认证多一次索引查询，换取权限变更、密码变更后的即时失效；Redis仍保存完整会话和权限，避免每次重新做角色权限多表查询。

续期使用EXPIRE而不是SET，避免并发退出后把删除的会话重新创建。退出直接DEL会话键。JWT和Redis必须同时有效。

## 功能权限与数据权限

角色名称可配置；实际判断使用 `approval:report:submit`、`approval:review:audit` 等权限标识。

功能权限回答“能否调用审核接口”；数据权限进一步回答“这份材料是否实际流转给当前用户”。没有查到自己对应的激活节点，即使有审核权限也看不到内容。

审核列表按提交轮次查询，详情读取该轮不可变快照。填报人修改、重提后，旧审批人仍只看旧轮，不能因为曾经参与过而看到后续未分配的数据。

## 提交事务

1. SELECT project FOR UPDATE锁定本人材料。
2. 检查当前状态和客户端版本。
3. 查询同一用户、同一requestId的成功提交，参数相同则重放结果，不重复建轮次。
4. 路径规划器查组织树和具有审核权限的有效用户；本级空选时跳过，向上寻找。
5. 新增project_submission快照和冻结的审批节点/候选人。
6. 只激活第一个节点，其余为WAITING。
7. 更新材料当前节点、状态和version，记录project_event。
8. 全部提交；中间任何失败都回滚。

相同幂等键不能换参数。前端结果未知时保留原键、版本和候选列表重试，不先重新保存或获取最新版本冒充原请求。

## 审核事务

锁材料 → 检查版本与当前节点 → 检查自己是待办候选人、非填报人、组织未变化 → 记录实际办理人 → 关闭同节点其他候选任务 → 激活下一节点或结束本轮 → 递增版本和记录事件。

同级两个人同时通过时，第二个请求等待材料锁，获得锁后因节点或版本已变化返回409。Redis不是审批正确性的唯一保障，数据库事务和版本才是业务最终约束。

撤回由本人在PENDING状态操作，取消本轮未结束任务并把材料恢复DRAFT。已有提交轮次仍保留，因此撤回材料不能作为“从未提交草稿”删除。

## 两种日志

- project_event：与材料更新同一个事务，成功的业务流转才落库。
- app_audit_log：通过@AuditAction与AuditAspect记录接口成功/失败，独立事务保存；失败时原业务异常不被日志错误掩盖。

审计不保存密码、JWT、Authorization或完整请求体。requestId关联浏览器响应、文件日志、数据库审计。

## V1迁移事实

V1没有记录材料历史快照，无法恢复不存在的历史内容，因此升级轮次的snapshotAvailable为false。旧节点激活时间依据已有办理时间或升级时间补录，仅作为访问资格迁移标识，不声称是完整历史时间。旧候选姓名也只能使用升级时可获得的资料。

## 参考来源与实现范围

- 若依：JWT与Redis联合验证、安全上下文、方法权限、分层和日志设计。https://doc.ruoyi.vip/ruoyi-vue/
- 芋道：角色权限及审批人、或签、历史记录等业务组织思路。https://github.com/YunaiV/ruoyi-vue-pro
- Spring Security：过滤链与方法授权。https://docs.spring.io/spring-security/reference/servlet/architecture.html
- JJWT：签发、验签、密钥要求。https://github.com/jwtk/jjwt

本项目没有复制它们的工程、封装类或流程引擎。固定分级或签的业务使用自己的Java实现；不是通用BPMN引擎，也不宣称已经完成生产安全审计。
