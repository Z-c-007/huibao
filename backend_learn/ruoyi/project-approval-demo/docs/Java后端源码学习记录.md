# Java 后端源码学习记录

更新于 2026-11-05 · 时间均为北京时间 · [架构地图与项目速览](Java后端架构与学习进度.md)

按实际学习时间记问题，按一次请求的执行顺序读代码。同一段在多个对话里继续问过，就合并到原来的链路。后来才问出来的卡点保留它出现的日期。源码片段来自当前工作区，示意数据和展开写法另有标注。对话中的「讲到」「自己复述」「实际运行」分别记录。

## 续学断点

**2026-11-05 晚 · 审批项目 `GET /api/auth/me`**。已经能说出请求先由过滤器检查，当前卡在「看到 `@AuthenticationPrincipal`，为什么下一步会想到找 `setAuthentication`？Controller 没调用 Service 或 Mapper，用户从哪进来的？」缺的前提是 **Spring MVC 会在调用 Controller 前解析方法参数，而 Spring Security 通过安全上下文把认证结果交给参数解析器**。下一次从[当前用户如何进入参数](#当前用户如何进入参数)接着读。

| 日期 | 当时推进到哪里 |
|---|---|
| 10-21 至 10-30 | 若依启动、阀井查询、论坛列表与回复、编辑事务、首次区分 JWT 和 Redis |
| 10-31 至 11-02 | 开始关注多表，从若依练习转到审批项目，跑通后从登录 Controller 开始读 |
| 11-03 | 请求参数和审计切面、两种登录计数、密码验证、Redis 会话、JWT 签发 |
| 11-04 | 带 JWT 的后续请求，区分启动时注册过滤器与请求时执行过滤器 |
| 11-05 | `/me` 的参数解析、当前用户的来源、在陌生工程里怎么追这条链 |

## 2026-10-21 至 10-30 · 若依里的第一条接口链

### 启动入口和外部服务

10-21 晚在 IDEA 导入若依，在 MySQL 建库并导入两份 SQL。最初问 Run 哪个 Java、缺 Redis 时是否必须用 WSL/Ubuntu，以及为什么装了 Memurai 后在 Windows 服务列表里找不到。10-22 自述 Java 课程到继承，选择做一次阀井基础信息 GET，要求用一组数据和熟悉的前端概念来讲。10-23 先让助手把演示写进工程，后面再亲自跑请求。

这里先把启动问题拆成三处。`RuoYiApplication` 是 Spring Boot 应用的入口。MySQL 和 Redis/Memurai 是应用依赖的独立服务。能连上端口、能通过账号认证、启动中的应用确实读取了所改的配置，是不同的验证步骤。真正收到接口响应后，还要判断响应来自认证层还是业务层。

### 阀井查询和分层

10-23 在《汇报后端进度演习》里问「有 Service 了为什么还有 Impl」。当天自述启动后直接访问 `/gis/valveWell/list` 收到 401，说明已经有一次真实请求和错误观察。10-25 自述跑过一遍，但读到 `ValveWell.java` 时以为下一步才去执行 SQL。10-26 先确认 Tomcat、过滤器和 Spring 路由的顺序，再问类上的 `@RequestMapping("/gis/valveWell")` 怎么和方法的 `/list` 组成完整路径。

要补的前提是**类的职责与运行顺序**。Service 接口声明可调用的业务操作，Impl 写实现，二者属于同一层。Mapper 接口的方法由 MyBatis 对应到 XML 语句，`namespace` 对应 Mapper 类型，语句 `id` 对应方法，`resultMap` 把查询结果列映射为 Java 属性。`ValveWell` 是用来接收数据的对象类型，读到其定义并不会发起查询。10-26 你已能顺着说出 `IValveWellService → ValveWellServiceImpl → ValveWellMapper → XML`，也能识别 `List<ValveWell>` 的元素类型和右侧的方法调用。此处进度记作已运行一次接口、能复述主要调用链。 [阀井演示][valve-guide] · [阀井 Controller][valve-controller] · [阀井 Mapper XML][valve-xml] · [MyBatis Mapper XML][mybatis]

### 论坛列表、新增和回复

10-26 晚到 10-27 早，导入论坛脚本时贴过 MySQL 1064，随后自述执行成功。留存的证据能确认先遇到语法错误、再成功，具体是哪段语句造成错误仍待核实。10-27 晚开始追 `@Validated`、`@Autowired`、`@PreAuthorize`、`@RequestParam`，以及 `@Positive`、`@Min`、`@Max` 是谁检查的。

- **列表怎么从请求到 SQL**。`@Autowired` 让 Spring 注入服务对象。`@RequestParam` 绑定请求参数，`@Validated` 和约束注解用于方法参数校验，`@Positive`、`@Min`、`@Max` 分别约束正数、下限和上限。Controller 先 `requireTopic(topicId)`，再 `startPage()`，让 PageHelper 把分页应用到接下来的评论列表查询。你自己顺到了 `forumService.selectComments(topicId)`、Mapper 和 XML 的 `topic_id=#{topicId} AND parent_id IS NULL`。入口参数校验、MyBatis 结果映射、响应 JSON 序列化各负责不同的数据转换或检查。 [论坛 Controller][forum-controller] · [论坛 Mapper XML][forum-xml] · [MyBatis Mapper XML][mybatis]
- **权限字符串怎么判断**。`@PreAuthorize("@ss.hasPermi('forum:comment:list')")` 表达调用名为 `ss` 的 Spring Bean 做权限判断。项目的 `PermissionService` 检查当前登录人的权限集合。字符串 `forum:comment:list` 是权限标识。请求路径由路由注解决定。你追到过 `SecurityUtils.getLoginUser()` 为什么不用传参数，这个若依方法从安全上下文读 principal，和 11-05 在审批项目追的参数解析是同一个数据来源问题。 [若依 PermissionService][ruoyi-permission] · [若依 SecurityUtils][ruoyi-utils]
- **回复为什么用父评论 ID**。10-27 你贴过成功的 `POST /forum/replies`，请求体 `topicId=1`、`parentId=3`，返回业务 `code=200`，然后对照查询 URL `GET /forum/comments/3/replies`。这里的路径参数 `commentId` 是要查看回复的父评论 ID，和新增回复时传的 `parentId` 指向同一行。10-28 又问「还没新增为什么先查」，顺着 `addReply → requireRootComment → save → insertComment` 可以看到，先确认已有评论可作为父评论，随后才构造新回复并写库。顶层评论的 `parent_id` 为 `NULL`。 [论坛 Controller][forum-controller] · [论坛 Service][forum-service] · [论坛 Mapper XML][forum-xml]
- **对象什么时候真正落库**。`ForumCommentRequest request` 的静态类型决定了 Java 可以调用哪些方法。你随后能自己说出 `new ForumComment` 和 setter 先构造内存对象，执行 Mapper 的 insert 才触发写库。你还问过为什么 Controller 只包 `success`。只有业务正常返回才会执行这句。抛出的异常走框架的异常处理。若依的 `AjaxResult` 包装普通响应，`TableDataInfo` 包装分页列表和总数，`@Log` 给操作审计提供元信息。 [论坛 Controller][forum-controller] · [论坛 Service][forum-service]

### 论坛编辑、权限和事务的初步接触

10-28 读 `ForumController.editComment` 时问 `@PathVariable` 的含义，以及 Service 里 `ForumComment target = requireManageable(commentId, reply)` 做了什么。10-29 能复述维护人员可增删改查、普通成员可查看和新增，继续问 `FOR UPDATE` 为什么要与更新放在同一个事务里。

这条链从 `@PutMapping` 匹配请求开始。`@PathVariable` 从 URL 模板取 ID，`@RequestBody` 读取 JSON，校验注解约束输入。`@PreAuthorize` 判断能否执行这个功能，Service 的 `requireManageable` 再检查目标评论能否由当前操作者处理，然后调用 Mapper 更新。你当时把 `@Transactional` 和「事务锁」放在一起问，也问了 `@Override`。三者分工如下。

| 名词 | 作用 |
|---|---|
| `@Override` | Java 编译器检查方法确实覆盖或实现了父类型中的声明。 |
| `@Transactional(rollbackFor = Exception.class)` | Spring 在适用的代理调用中定义事务范围和回滚规则。你已能用删除父评论和回复举例解释失败时为什么需要一起回滚。 |
| `SELECT … FOR UPDATE` | MySQL 的锁定读。在同一事务中锁住目标行再检查和更新，保护这段读改写。行锁实操当时只讨论了用途。 |

可对照编辑入口、事务实现和锁定读。 [论坛 Controller][forum-controller] · [论坛 Service][forum-service] · [论坛 Mapper XML][forum-xml] · [Spring 事务注解][spring-tx] · [MySQL 锁定读][mysql-locks]

10-29 至 10-30 还追过 IDEA 后端启动日志、Windows 上的 Memurai、Redis 客户端配置与服务端密码各在哪改。测试「故意改错仍能登录」时，重启是否生效、请求是否命中当前后端、登录是否真的访问 Redis 是三个待分开的证据。10-30 在《汇报学习后端整体概念》里能从前端经验推出登录返回 token、拦截器给后续请求加请求头，仍在问「是不是 `@PreAuthorize` 先解析 token」和「Redis 在哪一步查」。在若依代码中可分别看 token 认证过滤器、`TokenService` 和方法权限判断。这个问题后来在审批项目的 [过滤器执行顺序](#过滤器执行顺序) 里接上。 [若依认证过滤器][ruoyi-filter] · [若依 TokenService][ruoyi-token]

10-30 逐句执行过论坛演示 SQL，遇到报错和 `NULL` 后自述确认插入成功，并追问 SQL `SET`。其中 `INSERT INTO … SELECT … WHERE … EXISTS` 的读法是先单独跑 `SELECT` 看候选行，`EXISTS` 判断子查询有无结果，再把筛中的行写入目标表。`SET @变量 = …` 赋值给当前连接的用户变量，`UPDATE … SET 列 = …` 则更新表中匹配的行。脚本用 `ROW_COUNT()` 判断插入是否影响一行，再用 `LAST_INSERT_ID()` 取自增 ID 给后续 SQL 使用。当时看到变量为 `NULL` 的具体原因仍待核实，表中确有新增是后续自己确认的结果。 [论坛 SQL][forum-sql] · [MySQL INSERT … SELECT][mysql-insert] · [MySQL 用户变量][mysql-variables]

## 2026-10-31 至 11-02 · 转到审批项目，开始读登录

10-31 自述只看过 `INNER JOIN` 和 `LEFT JOIN`，想看真实的三到五张表和跨表写入。11-01 下午看过业务 SQL，仍在问「还是没理解，就是这么 LEFT JOIN 吗？」补的前提是先确定主表一行代表什么，再按关系写 `ON` 条件。内连接只保留匹配行，左连接保留左边的行，找不到右边记录时右侧列为 `NULL`。当时记为已接触 JOIN，独立设计关系和写查询待练。

11-01 晚提出了「本级多人任一通过、未选本级审批人则往上找、填报与审核分权」的业务练习。当天实际遇到 `CannotGetJdbcConnectionException`，追问启动入口、日志、DBeaver 建库和连接密码。11-02 早上自述已可用，晚上遇到前端 `undefined.join`，自己发现升级 SQL 尚未执行，之后继续处理 Redis 报错。这里记为在指导下启动和排查过，升级 SQL 与 Redis 连接问题按发生顺序分开记。 [审批项目运行说明][readme]

11-02 晚确定当前主线为 `project-approval-demo`，从 `AuthController.login` 开始。你问了登录路由、审计注解、响应包装、`User-Agent`、`HttpServletRequest` 和 `StringRedisTemplate`。11-03 回来继续读同一小段，已能说出 Service 收到了账号密码、IP 和客户端信息，并要求讲解时把两个同名的 `request` 区分开。

### 一次登录传了什么

```java
@PostMapping("/login")
@AuditAction(value = "LOGIN", category = "AUTH")
public ApiResponse<LoginResponse> login(
    @Valid @RequestBody LoginRequest body,
    HttpServletRequest request
) {
    request.setAttribute("loginUsername", body.username());
    String agent = request.getHeader("User-Agent");
    if (agent != null && agent.length() > 200) agent = agent.substring(0, 200);
    return ApiResponse.success(service.login(body, request.getRemoteAddr(), agent));
}
```

- **路由与请求体**。类上的 `@RequestMapping("/api/auth")` 与方法上的 `@PostMapping("/login")` 组成 `POST /api/auth/login`。Spring MVC 把请求体 JSON 转为 `LoginRequest body`，`@Valid` 触发对 DTO 约束的校验。`LoginRequest` 是项目的 Java record，`username()` 是 record 的访问方法。 [AuthController.java][auth-controller] · [LoginRequest.java][login-request] · [Spring MVC 请求体][spring-body] · [Java 17 record][java-record]
- **同名参数**。Controller 的 `request` 是 Jakarta Servlet 的 HTTP 请求对象，由容器提供，能读请求头、远端地址和服务端属性。Service 签名里的 `LoginRequest request` 就是 Controller 传下去的 `body`。它只承载登录业务数据。`getHeader("User-Agent")` 缺失时可以是 `null`，这段代码仍会调用 Service。`getRemoteAddr()` 读取直接连接对端地址。 [AuthController.java][auth-controller] · [AuthServiceImpl.java][auth-service] · [Jakarta Servlet 6.0][servlet]
- **请求属性和响应**。`setAttribute("loginUsername", …)` 把值放进当前请求，供审计在登录时尚无认证身份的情况下读取。它和客户端发送的请求头是两处数据。`ApiResponse.success(...)` 负责包装成功响应，输入校验已在前面的参数绑定阶段触发。 [AuditAspect.java][audit-aspect] · [ApiResponse.java][response]
- **对象怎么来的**。`AuthController(IAuthService service)` 表达它依赖一个服务对象。Spring 创建 Controller Bean 时提供依赖，通常通过项目的 `@Service AuthServiceImpl` 实现。Maven 声明库依赖，Java `import` 让代码能引用类型，Spring 依赖注入则负责把实际对象交到构造器里。 [IAuthService.java][auth-interface] · [AuthServiceImpl.java][auth-service] · [Spring 依赖注入][spring-di]

11-02 还问到「Spring 到底分别提供什么」。Spring Framework 提供容器、MVC 和 AOP 等基础。Spring Boot 帮项目启动并按依赖和配置装配组件。Spring Security 管认证、授权和相关过滤器。Spring Data Redis 提供 `StringRedisTemplate` 等数据访问 API。当前项目借这些能力编写登录规则、计数策略，以及 JWT 与会话的配合方式。 [项目依赖][pom] · [Spring 依赖注入][spring-di] · [Spring Security 过滤链][spring-filter] · [Spring Data Redis 模板][spring-redis]

## 2026-11-03 · 顺着登录读到底

### 审计注解为什么没有手动调用

11-02 晚先问 `@AuditAction` 的声明语法，11-03 上午接着问审计是否就是日志、为什么在 Controller 找不到显式保存调用。你认出了它和若依 `@Log` 类似。之后用一个 429 分支正确复述了异常会被记录、同时仍会抛给外层。14:08 又追问 `@Around("@annotation(action)")` 括号里的部分。

| 当时问到的名字 | 具体含义与这段代码的作用 |
|---|---|
| `@interface AuditAction`、`@Target(METHOD)`、`@Retention(RUNTIME)` | Java 的自定义注解和元注解。这里限定标记方法，并保留到运行时。 `String value()` 和带 `default` 的元素定义了项目可填写的审计信息。 |
| Spring AOP、AspectJ、`@Aspect` | Spring AOP 可通过代理在调用前后执行额外行为。项目使用 AspectJ 的注解和表达式风格声明切面。实际切入点是 Spring 管理对象的方法执行。 |
| `@Around("@annotation(action)")` | `@Around` 是环绕通知。字符串是切点表达式，匹配有对应注解的执行点，并把注解实例绑定给 `AuditAction action`，供切面读取操作名称和类别。 |
| `ProceedingJoinPoint point` | 类型来自 `org.aspectj.lang`，继承 `JoinPoint`，由 AOP 运行时传入。`point.proceed()` 会继续执行下一段通知或目标方法。 |
| `catch (Throwable e)`、`instanceof BusinessException b` | `catch` 接到抛出的对象，`instanceof … b` 在类型匹配时绑定 `b`。项目用多层三元表达式为审计选择状态，例如业务异常取自己的状态。末尾 `throw e` 把原异常继续交给外层。 |
| `finally`、`MDC`、请求属性 | `finally` 处理成功和失败两种结果。SLF4J 的 `MDC` 是附加日志上下文，项目从中取 `requestId`。登录时还可以从请求属性读取尝试登录的用户名。审计记录通过 `AuditLogService.save` 独立写入。 |

可把这段想成「进入切面并计时 → `point.proceed()` 执行登录 → 取得返回值或异常 → `finally` 写审计 → 原来的返回或异常继续」。这个模型解释了为什么 Controller 只写一个注解也能产生审计记录。已能按例子解释失败分支，暂未见自己打断点核对审计入库的记录。 [AuditAction.java][audit-action] · [AuditAspect.java][audit-aspect] · [AuditLogService.java][audit-service] · [Spring AOP 通知][spring-aop] · [AspectJ ProceedingJoinPoint][aspectj] · [SLF4J MDC][slf4j-mdc] · [Java Retention][java-retention] · [Java instanceof 模式匹配][java-instanceof]

### 两种登录计数和 Redis 的读写

11-03 白天从 `AuthServiceImpl.login` 追到 `attempts.check(username, ip)`，问为什么需要计数。你曾把「60 秒还没过期」当成「还能查 MySQL」，也问过 Java 局部变量 `failures = "5"` 和 Redis 写入 `"3"` 分别改变什么。晚间交接时明确停在读取账号失败次数这一句。 [AuthServiceImpl.java][auth-service] · [LoginAttemptService.java][login-attempts]

```java
String failures = redis.opsForValue().get(account(username));
if (failures != null && Integer.parseInt(failures) >= properties.maxLoginFailures()) {
    throw new BusinessException(429, "账号登录失败次数过多，请在锁定时间结束后重试");
}
```

- **`StringRedisTemplate`** 是 Spring Data Redis 提供的客户端操作模板，负责连接和字符串序列化等细节。它是注入进 `LoginAttemptService` 的 Java 对象。`opsForValue()` 取字符串值操作接口，`get(key)` 到 Redis 读取值。`account(username)` 只是算出键名，由前缀、用途和用户名的哈希组成。读到 `"3"` 后，Java 局部变量只是收到这个结果。给变量重新赋值也不会写回 Redis。 [Spring Data Redis 模板][spring-redis] · [LoginAttemptService.java][login-attempts]
- **按 IP 的计数**。每次调用 `check` 都先增加 IP 的请求次数。Lua 脚本把 `INCR` 和首次设置 `EXPIRE` 放在一起，`KEYS[1]` 是键，`ARGV[1]` 是过期秒数。`DefaultRedisScript<Long>` 是 Spring Data Redis 对脚本的封装，返回类型是 `Long`。源码传 60 秒，`requests <= 30` 才继续。以第 31 次为例，即使 key 的 TTL 仍大于 0，也已经在这里返回 429，后面的 MySQL 查用户不会执行。 [LoginAttemptService.java][login-attempts] · [Redis Lua][redis-lua] · [Redis EXPIRE][redis-expire]
- **按账号的失败计数**。`check` 先读已有失败值。没有键时得到 `null`，`&&` 短路会跳过后面的比较。有值时用 `Integer.parseInt` 把例如 `"3"` 转成整数。`failed(username)` 在账号不存在、密码不匹配或账号停用时增加失败次数。当前这次凭证错误走 401，后续请求如果命中已达阈值的计数，才在前置检查走 429。默认阈值为 5 次，窗口 600 秒。假设 10:00 首次失败，10:06 第五次失败，之后命中阈值就先返回 429，原窗口仍在 10:10 到期。后续增加次数不会重新起算。 [LoginAttemptService.java][login-attempts] · [AuthServiceImpl.java][auth-service] · [项目配置说明][readme]
- **成功为什么 `DEL`**。`attempts.success(username)` 清掉的是该账号的失败计数键，下一次再失败会从新的一次计数开始。IP 计数仍按原窗口过期，已建立的登录会话存在另一类键。晚间你已能复述 IP 与账号计数的用途区别，账号窗口起点和两种响应状态还值得用具体例子核对。 [LoginAttemptService.java][login-attempts] · [Redis 会话][redis-session]

### 查询用户、哈希和统一失败分支

21:41 你表示能读懂 `users.selectByUsername(username)`，问 `dummyHash`、`@JsonIgnore` 的作用。21:54 推断 `PasswordEncoder.matches` 是拿输入密码和存储哈希验证。21:56 问接下来的 `if` 是否还在做密码匹配。

1. `request.username().strip()` 去掉用户名首尾空白，`UserMapper.selectByUsername` 查询并映射为 `AppUser`。Mapper 对应的 SQL 在 XML。 [登录服务][auth-service] · [用户 Mapper XML][user-xml]
2. 找不到用户时选预先生成的 `dummyHash`，这样正常长度的输入仍走一次哈希比对，减少从响应耗时推测账号是否存在的机会。`PasswordEncoder` 是 Spring Security 的接口，此处 Bean 实际由 `SecurityConfig` 创建为 `BCryptPasswordEncoder(12)`。 `matches(输入密码, 存储哈希)` 验证输入。`getBytes(StandardCharsets.UTF_8).length <= 72` 比的是 UTF-8 字节数，避免把字符数和 BCrypt 的输入限制混用。 [登录服务][auth-service] · [安全配置][security-config] · [Spring Security 密码存储][spring-password]
3. `user == null || !matched || !Boolean.TRUE.equals(user.getEnabled())` 汇总三个失败条件。`||` 会短路，第一项为真就不会访问空对象。密码匹配结果在前面已经算成 `matched`，这里决定是否记失败并统一抛 401。 [登录服务][auth-service]
4. `@JsonIgnore` 来自 Jackson，影响它对属性的 JSON 读写。项目把它放在 `passwordHash` 上，防止该属性按普通字段进入 JSON。服务内读取哈希、MyBatis 从数据库映射字段属于另外的访问路径。 [AppUser.java][app-user] · [Jackson JsonIgnore][jackson-ignore]

### CurrentUser、会话数据和两种时间

21:58 你把 `new CurrentUser(...)` 与 `sessions.create(current, ip, userAgent)` 放在一起问。22:16 表示能看懂字面代码，但要弄清 Redis 来回传了什么。以一次示意登录为例，按下面的值看每一步。

| 步骤 | 输入和输出 |
|---|---|
| 组装 `CurrentUser` | 从 `AppUser` 取用户和组织信息，再查角色与权限。 `List.copyOf` 生成不可修改的列表。 `authVersion` 是项目自己的版本号，用于判断旧身份是否应失效。 |
| 构造 `LoginSession` | 输入 `CurrentUser`、IP 和 User-Agent。生成会话 ID，加入签发时间、绝对到期时间。 |
| 保存会话和索引 | Jackson `ObjectMapper` 把会话对象序列化成 JSON 字符串。`opsForValue().set` 写会话键和空闲 TTL，`opsForSet().add` 将会话 ID 放入该用户的会话集合，供列表或撤销使用。 |
| 后续按 ID 读回 | Redis 返回 JSON 字符串，`ObjectMapper.readValue` 还原成 `LoginSession`。键不存在时 `find` 返回 `null`。 |

此处「序列化」就是把 Java 对象转换成可以存储的字符串，「反序列化」是读取字符串后重建 Java 对象。用户索引 Set 存的是会话 ID，完整用户数据在会话值中。 [AuthServiceImpl.java][auth-service] · [CurrentUser.java][current-user] · [LoginSession.java][login-session] · [RedisSessionService.java][redis-session] · [Spring Data Redis 模板][spring-redis]

22:22 问请求会不会重置到期时间，22:26 已能自己举例说明。10:00 登录，绝对期限是 18:00，17:55 发请求也不会把绝对期限推到 18:25。项目默认 JWT 的绝对有效期为 8 小时，Redis 会话空闲有效期为 30 分钟，临近 10 分钟才考虑续期。读 `touch` 时看会话是否仍存在、是否临近空闲到期、离绝对到期还剩多久。符合条件才用 `EXPIRE` 续期，新 TTL 取空闲时长和绝对剩余时间中的较小值。在例子里 17:55 的请求要先通过验证，即使续期也最多再给 5 分钟。`EXPIRE` 只改已有键的过期时间，避免重新创建已撤销的会话。已能解释绝对到期示例，实际 TTL 还没看到本人验证记录。 [RedisSessionService.touch][redis-session] · [项目配置说明][readme] · [Redis EXPIRE][redis-expire]

### LoginResponse 和 JWT 的签发

22:35 读到 `return new LoginResponse(jwt.create(session), "Bearer", properties.tokenMinutes() * 60L, current)`，大致能读懂返回值，明确提出 JWT 要继续补。

- **JWT 与 Bearer**。JWT 是携带声明的令牌格式。这个项目签发带 HS512 签名的 JWT，`Bearer` 表明客户端后续如何放进请求头。看懂 Base64URL 载荷只是解码，可信性需要验签和检查声明。 [JwtTokenProvider.java][jwt-provider] · [JWT RFC 7519][jwt-rfc] · [Bearer RFC 6750][bearer-rfc]
- **声明与项目字段**。`iss` 是签发方，`sub` 是用户 ID，`jti` 在本项目用作会话 ID，`iat` 是签发时间，`exp` 是绝对到期时间，`authVersion` 是自定义声明。权限列表在 Redis 会话里。`60L` 的 `L` 表示 `long`，这里把分钟转成秒给响应。 [JwtTokenProvider.java][jwt-provider] · [AuthServiceImpl.java][auth-service]
- **签发与验证谁做什么**。项目决定放哪些声明并调用 JJWT。库提供令牌构建、验签和解析。`verify` 通过 `verifyWith` 和 `requireIssuer` 配置解析器，再用 `parseSignedClaims` 读取已验证的声明。项目检查必要字段，构造 `VerifiedToken` 给过滤器。学习深度先到输入、输出、失败条件，之后再按实际问题深入库内部。 [JwtTokenProvider.java][jwt-provider] · [JJWT 0.12.6 JwtParser][jjwt]

### 当晚 Redis 概念支线

22:53 开始带 JWT 读后续请求。在辅助对话中先读到 `jwt.verify` 得出 `VerifiedToken`，下一句是按会话 ID 查 Redis。这次用示意值走读。23:07 主动复述了应用先查 Redis、未命中再查 MySQL 并回填的过程，这是 cache-aside 的基本思路。随后又问到远程共享缓存、本地缓存、单线程并发、TTL、淘汰和持久化，可以分开复习。 [Redis cache-aside][redis-cache-aside]

| 术语 | 应该怎样区分 |
|---|---|
| 本地缓存与远程缓存 | 本地缓存随应用进程各有一份。多个后端实例可通过网络访问同一个 Redis。应用实例还是各自运行，共享的是访问的数据服务。 |
| Redis 命令与并发 | 一段 Redis Lua 可以原子执行。应用先 `GET` 再根据结果 `SET` 是两次调用，中间仍可能有其他请求。 |
| TTL 与淘汰 | TTL 是给某个键设置失效时间。内存达到限制时是否驱逐、驱逐哪些键由淘汰策略决定，LRU 类策略关注最近使用情况。 |
| RDB、AOF 与故障 | RDB 保存时间点快照，AOF 记录写操作以便重放。持久化用于恢复 Redis 数据。应用在 Redis 不可用时怎样应对、会不会把请求打到 MySQL，是另一个运行问题。 |
| RESP 与 TCP | RESP 规定 Redis 客户端与服务端如何编码命令和响应，通常在 TCP 连接上传输。TCP 管传输，RESP 管应用层消息格式。 |

当前审批工程用 Redis 保存会话和计数。Redis 不可用时，认证链上的依赖异常会按项目处理为 503。缓存回填、淘汰和恢复都属于通用支线，目前记录为接触过概念。 [认证过滤器][jwt-filter] · [Redis Lua][redis-lua] · [Redis 淘汰][redis-eviction] · [Redis 持久化][redis-persistence] · [Redis RESP][redis-resp]

## 2026-11-04 · 带 token 的请求为什么先走过滤器

### 过滤器执行顺序

11-04 上午看 `AuthController.me` 时问「就这几行代码，为什么会走到 SecurityConfig？」晚上继续追问「Spring 执行顺序怎么决定」「是不是在哪里用 Spring Security API 都会在过滤器执行」「怎么写才算注册过滤器」。这组问题要拆开**应用启动时配置链**和**每次请求时走链**。

| 时间 | 谁做什么 |
|---|---|
| 应用启动 | Spring 创建 `SecurityFilterChain` Bean，`SecurityConfig.securityFilterChain` 用 `.addFilterBefore(filter, UsernamePasswordAuthenticationFilter.class)` 定义 JWT 过滤器在安全链里的相对位置。项目用禁用的 `FilterRegistrationBean` 避免同一个 JWT 过滤器又按普通 Servlet Filter 注册一遍。 |
| 收到请求 | Servlet 容器先运行匹配的过滤链，Spring Security 在其中选择并运行相应的安全链。项目的 `JwtAuthenticationFilter.doFilterInternal` 因此会在 MVC 调 Controller 前执行。 |
| 放行与返回 | 过滤器调用 `chain.doFilter(request, response)`，把请求交给后续过滤器或 Servlet。这个调用之前可以检查，调用返回后也可以继续执行当前过滤器中的后置代码。过滤器写出错误并提前返回时，后续链不会走。 |

关键字对应不同层次。`@Configuration` 声明配置类，`@Bean` 声明由 Spring 管理的对象，`@Component` 让组件可被扫描。把实例加入安全链靠这里的 `addFilterBefore`。`UsernamePasswordAuthenticationFilter.class` 在这句里用作顺序参照。11-05 你用「执行前的过滤器类、执行后的过滤器类」复述。更具体的模型是**同一个过滤器也能把代码写在 `chain.doFilter` 前后**，各过滤器还能按链的顺序嵌套执行。 [SecurityConfig.java][security-config] · [JwtAuthenticationFilter.java][jwt-filter] · [Spring Security 过滤链][spring-filter]

过滤器拿到 `Authorization` 以后，从 `Bearer ` 后面取字符串，调用 `jwt.verify`，再按已验证的会话 ID 查 Redis。会话有效时还要查 MySQL 的账号启用状态、组织和权限版本，之后才设置认证信息。有效的凭证和会话解决身份识别，`@PreAuthorize` 等规则再决定能不能操作特定接口。登录路径由 `shouldNotFilter` 跳过这段 JWT 认证，因为它正是获取初始登录凭证的入口。 [JwtAuthenticationFilter.java][jwt-filter] · [JwtTokenProvider.java][jwt-provider] · [SecurityConfig.java][security-config]

## 2026-11-05 · 从 Controller 反查用户参数的来源

### 当前用户如何进入参数

21:24 开始看 `@AuthenticationPrincipal`。21:41 问「`/me` 没调用 Service 或 Mapper，是怎么取到数据的？」22:00 你能复述过滤器失败就不会到接口，但进一步问陌生项目里如何找。22:10 进一步问「为什么看到 `AuthenticationPrincipal`，就全局搜 `setAuthentication`？」这是**方法参数是谁传入的**问题，可以先从消费端追到框架约定，再到产生数据的项目代码。

```java
@GetMapping("/me")
public ApiResponse<CurrentUser> me(@AuthenticationPrincipal CurrentUser user) {
    return ApiResponse.success(user);
}
```

**框架如何把参数准备好。** Spring MVC 已匹配到 `me`，需要在调用前为每个形参准备实参。`AuthenticationPrincipalArgumentResolver` 由 Spring Security 提供，识别这个注解，然后读取当前 `Authentication.getPrincipal()`。它把 principal 作为 `user` 实参传给 Controller。这和 `@RequestBody` 都属于运行时解析方法参数，但数据来源不同，一个来自安全上下文，一个来自 HTTP 请求体。 [AuthController.java][auth-controller] · [Spring Security MVC 参数解析][spring-principal] · [Spring MVC 请求体][spring-body]

**数据怎样跨过过滤器和 Controller。** `SecurityContextHolder` 是访问安全上下文的入口，`SecurityContext` 保存 `Authentication`，`Authentication` 里面才有 principal 和 authorities。Servlet 模式默认使用线程本地存储，当前处理线程上的代码能访问上下文，安全过滤链结束时框架负责清理。类名里的静态入口和存储作用域是两回事。Java 的 `import` 只告诉编译器代码在引用哪个类型，Controller 的 `user` 值由框架这次调用时准备。这里也和前端项目的全局对象不同，身份数据有请求处理的生命周期。 [Spring Security 认证架构][spring-context]

**本项目在哪里写进去。** 看 `JwtAuthenticationFilter.doFilterInternal` 的下面几行。 `session.user()` 来自 Redis 会话，`authorities` 从会话权限转换，`null` 是传入的 credentials。调用 `authenticated` 组装已经通过项目检查的身份，随后写入上下文。

```java
var authentication = UsernamePasswordAuthenticationToken.authenticated(
    session.user(),
    null,
    authorities
);
authentication.setDetails(
    new WebAuthenticationDetailsSource().buildDetails(request)
);
SecurityContextHolder.getContext().setAuthentication(authentication);
request.setAttribute("loginSessionId", session.sessionId());
```

`UsernamePasswordAuthenticationToken` 在这里是 Spring Security 的 `Authentication` 实现，承载认证结果。HTTP 请求头里的 JWT 是客户端提供的字符串，两者分别存在于不同阶段。`setDetails` 附加 Web 请求详情。`loginSessionId` 另存到 Servlet 请求属性，供退出或会话接口读取，`@AuthenticationPrincipal` 取当前用户走的是安全上下文。 [JwtAuthenticationFilter.java][jwt-filter] · [AuthController.java][auth-controller] · [Spring Security 认证架构][spring-context]

**在陌生项目里怎样追。**

1. 从参数的注解 import 确认是 Spring Security 的 `@AuthenticationPrincipal`。查官方 MVC 集成说明或跳进 `AuthenticationPrincipalArgumentResolver`，确认它读的是 `Authentication.getPrincipal()`。
2. 确认认证信息存在 `SecurityContext`，再找这个工程**谁写入该上下文**。当前项目搜 `setAuthentication(` 直接命中 JWT 过滤器。换项目时，写入也可能由框架过滤器完成。这时先看 `SecurityFilterChain` 和启用的认证机制，再从过滤器或调试调用栈定位。
3. 回到 JWT 过滤器，从构造认证对象的 `session.user()` 继续追到 `sessions.find`。这才解释了 `/me` 的用户数据在这个工程里从哪来。每次请求还会查询数据库的账号安全状态，这段 SQL 位于认证链路，并未写在 `me()` 里。 [Spring Security MVC 参数解析][spring-principal] · [SecurityConfig.java][security-config] · [JwtAuthenticationFilter.java][jwt-filter]

用一条数据流复习。浏览器的 Bearer 字符串 → 过滤器里的 `VerifiedToken` → Redis 的 `LoginSession` → `session.user()` → `Authentication.principal` → 安全上下文 → MVC 参数解析器 → `me(CurrentUser user)`。同一枚 JWT 可先请求 `GET /api/auth/me`，通过 `POST /api/auth/logout` 撤销当前测试会话，再用旧 token 请求。前一次可对照过滤器写入和 Controller 实参，后一次预期在查会话后返回 401。另一次无请求头的 401 可用来区分是哪一层拦截。**状态**已能复述过滤器先于 Controller，参数解析与框架上下文是当前补充解释，独立断点结果待记录。 [AuthController.java][auth-controller] · [JwtAuthenticationFilter.java][jwt-filter]

## 术语索引

| 想查什么 | 回到哪一节 |
|---|---|
| Controller、Service/Impl、Mapper、XML、namespace、resultMap、泛型 | [阀井查询和分层](#阀井查询和分层) |
| PageHelper、权限 Bean、父评论 ID、对象落库、AjaxResult | [论坛列表、新增和回复](#论坛列表新增和回复) |
| Servlet 请求、HTTP 参数、请求属性、DTO、record、Bean、依赖注入 | [一次登录传了什么](#一次登录传了什么) |
| AspectJ、AOP、环绕通知、切点、`ProceedingJoinPoint`、`MDC`、异常重抛 | [审计注解为什么没有手动调用](#审计注解为什么没有手动调用) |
| `StringRedisTemplate`、`opsForValue`、Lua、`INCR`、`EXPIRE`、429 | [两种登录计数和 Redis 的读写](#两种登录计数和-redis-的读写) |
| `PasswordEncoder`、BCrypt、dummy hash、`@JsonIgnore` | [查询用户、哈希和统一失败分支](#查询用户哈希和统一失败分支) |
| 会话、序列化、TTL、Set 索引、绝对有效期、续期 | [CurrentUser、会话数据和两种时间](#currentuser会话数据和两种时间) |
| JWT、Bearer、`jti`、`exp`、`authVersion`、JJWT | [LoginResponse 和 JWT 的签发](#loginresponse-和-jwt-的签发) |
| Cache-aside、远程缓存、淘汰、RDB、AOF、RESP | [当晚 Redis 概念支线](#当晚-redis-概念支线) |
| `SecurityFilterChain`、`addFilterBefore`、`chain.doFilter`、`@PreAuthorize` | [过滤器执行顺序](#过滤器执行顺序) |
| 参数解析器、`@AuthenticationPrincipal`、principal、`SecurityContextHolder`、`ThreadLocal` | [当前用户如何进入参数](#当前用户如何进入参数) |

## 记录依据与续写

- 早期经历来自《汇报后端进度演习》《论坛后端功能开发》《汇报学习后端整体概念》。审批主线来自《后端功能开发学习》《学习后端_new》《学习后端_new_辅助理解其他概念》。11-03 多个对话重复的登录带读按同一条链合并。
- 框架术语按项目 `pom.xml` 对应的 Java 17、Spring Boot 3.5 系列、Spring Framework 6.2、Spring Security 6.5、Spring Data Redis 3.5 和 JJWT 0.12.6 查阅。代码与配置值以仓库为准。 [后端依赖][pom]
- 继续记录时，先记日期和实际问题，再写文件与方法、对象来源、输入和输出、已能解释或验证的证据，以及下次接入点。认证收口后的主线是「我的项目」分页查询、待审列表数据权限、提交审批事务。 [架构地图的后续练习](Java后端架构与学习进度.md#后续练习)

[valve-guide]: ruoyi/RuoYi-Vue-springboot3/doc/阀井基础信息查询演示.md
[valve-controller]: ruoyi/RuoYi-Vue-springboot3/ruoyi-admin/src/main/java/com/ruoyi/web/controller/gis/ValveWellController.java
[valve-xml]: ruoyi/RuoYi-Vue-springboot3/ruoyi-system/src/main/resources/mapper/system/ValveWellMapper.xml
[forum-controller]: ruoyi/RuoYi-Vue-springboot3/ruoyi-admin/src/main/java/com/ruoyi/web/controller/forum/ForumController.java
[forum-service]: ruoyi/RuoYi-Vue-springboot3/ruoyi-system/src/main/java/com/ruoyi/system/service/impl/ForumServiceImpl.java
[forum-xml]: ruoyi/RuoYi-Vue-springboot3/ruoyi-system/src/main/resources/mapper/system/ForumMapper.xml
[forum-sql]: ruoyi/RuoYi-Vue-springboot3/sql/forum_crud_presentation.sql
[ruoyi-filter]: ruoyi/RuoYi-Vue-springboot3/ruoyi-framework/src/main/java/com/ruoyi/framework/security/filter/JwtAuthenticationTokenFilter.java
[ruoyi-token]: ruoyi/RuoYi-Vue-springboot3/ruoyi-framework/src/main/java/com/ruoyi/framework/web/service/TokenService.java
[ruoyi-permission]: ruoyi/RuoYi-Vue-springboot3/ruoyi-framework/src/main/java/com/ruoyi/framework/web/service/PermissionService.java
[ruoyi-utils]: ruoyi/RuoYi-Vue-springboot3/ruoyi-common/src/main/java/com/ruoyi/common/utils/SecurityUtils.java
[readme]: ruoyi/project-approval-demo/README.md
[pom]: ruoyi/project-approval-demo/backend/pom.xml
[auth-controller]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/controller/AuthController.java
[auth-interface]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/service/IAuthService.java
[auth-service]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/service/impl/AuthServiceImpl.java
[response]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/common/ApiResponse.java
[login-request]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/dto/request/LoginRequest.java
[audit-action]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/audit/AuditAction.java
[audit-aspect]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/audit/AuditAspect.java
[audit-service]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/service/AuditLogService.java
[login-attempts]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/security/LoginAttemptService.java
[current-user]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/security/CurrentUser.java
[app-user]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/domain/AppUser.java
[user-xml]: ruoyi/project-approval-demo/backend/src/main/resources/mapper/UserMapper.xml
[login-session]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/security/LoginSession.java
[redis-session]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/security/RedisSessionService.java
[jwt-provider]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/security/JwtTokenProvider.java
[jwt-filter]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/security/JwtAuthenticationFilter.java
[security-config]: ruoyi/project-approval-demo/backend/src/main/java/com/learning/approval/config/SecurityConfig.java
[mybatis]: https://mybatis.org/mybatis-3/sqlmap-xml.html
[mysql-insert]: https://dev.mysql.com/doc/refman/8.4/en/insert-select.html
[mysql-variables]: https://dev.mysql.com/doc/refman/8.4/en/user-variables.html
[mysql-locks]: https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html
[spring-body]: https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-methods/requestbody.html
[java-record]: https://docs.oracle.com/en/java/javase/17/language/records.html
[spring-di]: https://docs.spring.io/spring-framework/reference/6.2/core/beans/dependencies/factory-collaborators.html
[spring-aop]: https://docs.spring.io/spring-framework/reference/6.2/core/aop/ataspectj/advice.html
[aspectj]: https://eclipse.dev/aspectj/doc/latest/runtime-api/org/aspectj/lang/ProceedingJoinPoint.html
[slf4j-mdc]: https://www.slf4j.org/apidocs/org/slf4j/MDC.html
[spring-redis]: https://docs.spring.io/spring-data/redis/reference/3.5/redis/template.html
[spring-password]: https://docs.spring.io/spring-security/reference/6.5/features/authentication/password-storage.html
[jackson-ignore]: https://javadoc.io/static/com.fasterxml.jackson.core/jackson-annotations/2.21/com/fasterxml/jackson/annotation/JsonIgnore.html
[redis-expire]: https://redis.io/docs/latest/commands/expire/
[redis-lua]: https://redis.io/docs/latest/develop/programmability/eval-intro/
[redis-eviction]: https://redis.io/docs/latest/develop/reference/eviction/
[redis-persistence]: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
[redis-resp]: https://redis.io/docs/latest/develop/reference/protocol-spec/
[redis-cache-aside]: https://redis.io/docs/latest/develop/use-cases/cache-aside/
[jwt-rfc]: https://www.rfc-editor.org/rfc/rfc7519.html
[bearer-rfc]: https://www.rfc-editor.org/rfc/rfc6750.html
[jjwt]: https://javadoc.io/static/io.jsonwebtoken/jjwt-api/0.12.6/io/jsonwebtoken/JwtParser.html
[spring-filter]: https://docs.spring.io/spring-security/reference/6.5/servlet/architecture.html
[spring-context]: https://docs.spring.io/spring-security/reference/6.5/servlet/authentication/architecture.html
[spring-principal]: https://docs.spring.io/spring-security/reference/6.5/servlet/integrations/mvc.html#authentication-principal
[spring-tx]: https://docs.spring.io/spring-framework/reference/6.2/data-access/transaction/declarative/annotations.html
[servlet]: https://jakarta.ee/specifications/servlet/6.0/
[java-retention]: https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/annotation/Retention.html
[java-instanceof]: https://docs.oracle.com/en/java/javase/17/language/pattern-matching-instanceof.html
