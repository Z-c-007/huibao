# 论坛评论与维护人员回复 Demo

> 2026-10-28：已补充编辑、删除，权限升级、Redis流程和SQL示例见同目录《论坛CRUD与Redis讲解.md》。下面的初始交付状态属于早期记录；用户已自行完成初始建表并看到评论/回复效果。本次新增权限脚本仍需管理员执行，不代表新增功能已完成真实数据库联调。

## 当前交付状态

- 已实现官方若依 Vue3 前端、真实登录接入、动态菜单、评论与一级维护回复。
- 后端业务与权限测试已通过，前端生产构建已通过。
- 浏览器UI检查已通过：成员评论、刷新、维护人员回复、按钮差异与390px移动布局。
  该检查仅在隔离浏览器中拦截接口并提供测试数据，不修改应用实现，不写数据库。
- **尚未完成本机数据库初始化和真实账号联调。** 当前 `ruoyi_app` 没有 CREATE 权限，
  初始化命令在第一条建表语句被拒绝，未创建本模块表和演示用户。用户选择暂不导入。
- 下面描述的是导入后应执行的演示，不把预期行为当成已经验证的行为。
- 页面使用真实 API，没有放入生产代码的假登录或假评论数据。

## 目录与环境

- 后端：`D:\GIS_learn\backend_learn\ruoyi\RuoYi-Vue-springboot3`
- 前端：`D:\GIS_learn\backend_learn\ruoyi\RuoYi-Vue3`
- Java：使用项目配置的 Java 17；本机JDK路径 `D:\develop\Java`。
- 前端为官方3.9.2 JavaScript版，来源提交见前端 `UPSTREAM.md`。
- 本机前端构建使用 Node.js 24.19.0，依赖锁文件为 `package-lock.json`。
- MySQL、Redis/Memurai需要正常运行，账号连接继续使用现有后端配置。

## 1. 一次性初始化数据库

在 Navicat、MySQL Workbench 或 IDEA 的数据库窗口，用**已有的数据库管理员账号**
连接本机 MySQL，选中与后端一致的 `ry-vue`，执行：

`sql/forum_demo.sql`

不需要重新导入若依全套SQL，不需要修改 ruoyi_app 的权限。
应用账号如果原本具有 `ry-vue.*` 的读写权限，新表创建后即可正常使用。
若只对部分表授权，应由数据库管理员为新表配置应用需要的最小读写权限。

脚本新增：

- `biz_forum_topic`、`biz_forum_comment`。
- 固定主题“阀井台账系统使用反馈”。
- 角色 `forum_member`、`forum_operator`。
- 账号 `forum_member`、`forum_operator`。
- “反馈讨论 → 讨论区”菜单与对应按钮权限。

两个新账号的本地演示初始密码均为：`ForumDemo2026!`。
数据库保存的是BCrypt哈希。仅用于本地演示，正式环境请独立设置凭据。
重复运行不删除评论、不重置密码、不覆盖已有账号；若遇到同名非Demo对象则中止。
脚本依赖MySQL8 CHECK约束，当前本机为8.0.45。

数据库脚本包含事务，但建表DDL会自动提交；若发生中途错误，先检查报错再重试。
已有同名表时先确认结构兼容；本次执行尚未创建表，因此没有需要清理的半成品。

## 2. 启动后端

IDEA使用 `RuoYiApplication`，默认数据源Profile为 `druid`。
**论坛不需要 valve-well-demo Profile，也不能匿名访问。** 原阀井示例可以保留。
后端默认端口8080。若已有旧实例，正常停止该实例，再启动更新后的代码。

命令行构建与运行的另一种方式（PowerShell，在后端根目录）：

```powershell
$env:JAVA_HOME = 'D:\develop\Java'
mvn.cmd -B -ntp -pl ruoyi-admin -am package
& 'D:\develop\Java\bin\java.exe' -jar '.\ruoyi-admin\target\ruoyi-admin.jar' --spring.profiles.active=druid
```

等待“若依启动成功”。若8080已被其他程序占用，先确定归属，不要直接结束未知进程。

## 3. 启动前端

PowerShell进入前端目录：

```powershell
Set-Location 'D:\GIS_learn\backend_learn\ruoyi\RuoYi-Vue3'
npm.cmd ci --no-audit --no-fund
npm.cmd run dev
```

本机依赖已安装时可以跳过 `npm ci`。浏览器打开：

`http://127.0.0.1:5173/login?redirect=/forum/discussion`

在正常登录页输入账号、密码与验证码，登录后进入讨论区。
也可以从侧边栏“反馈讨论 → 讨论区”进入。

Vite代理：前端 `/dev-api` 转发到 `http://127.0.0.1:8080` 并去掉前缀。
如果后端改端口，在前端新建 `.env.development.local`：

```text
VITE_BACKEND_TARGET=http://127.0.0.1:8081
```

然后重启前端。该本地文件被gitignore忽略，不需要修改全局跨域规则。
正式部署时按若依常规方式配置网关反向代理，不使用Vite开发服务器作为生产服务。

## 4. 两个账号的权限

| 能力 | forum_member | forum_operator |
|---|---|---|
| 查看主题、评论和回复 | 可以 | 可以 |
| 发表评论 | 可以 | 可以 |
| 维护人员回复 | 不可以 | 可以 |
| 系统用户/角色管理 | 不可以 | 不可以 |

两者都不是超级管理员。成员没有 `forum:reply:add`，所以直接调接口也应被拒绝。
普通浏览器与无痕窗口、或两个不同浏览器登录，避免共享Cookie造成身份混淆。
如果初始化或修改权限时已有旧登录，请重新登录后再验证。

## 5. 五分钟演示顺序（导入后执行）

1. 普通成员登录，进入同一固定主题，发表“建议支持按阀井编号查询”。
2. 刷新页面，确认评论仍存在且作者正确。
3. 在独立浏览器环境用维护人员登录，看到评论，点击“维护人员回复”。
4. 回复“已记录，后续评估筛选功能”；普通成员刷新并点击“查看回复”。
5. 普通成员页面没有维护人员回复入口；用该成员token直接请求回复接口，检查业务code为403且数据库记录数不变。
6. 打开Controller展示权限注解，再沿Service、Mapper、XML说明保存链路。

本项目权限拒绝通常通过HTTP 200响应体中的 `code:403` 表达；未认证为 `code:401`。
不能只看HTTP状态码判断业务成功，也不为此修改若依全局异常处理。
真实运行时应记录实际HTTP和业务码。

## 6. API契约

所有接口必须携带 `Authorization: Bearer <真实登录token>`。

| 方法/路径 | 参数 | 权限 | 响应 |
|---|---|---|---|
| GET /forum/topic | 无 | forum:topic:query | AjaxResult.data：固定主题 |
| GET /forum/comments | topicId、pageNum、pageSize | forum:comment:list | TableDataInfo.rows/total |
| GET /forum/comments/{commentId}/replies | topicId、pageNum、pageSize | forum:comment:list | TableDataInfo.rows/total |
| POST /forum/comments | JSON：topicId、content | forum:comment:add | AjaxResult.data：新评论 |
| POST /forum/replies | JSON：topicId、parentId、content | forum:reply:add | AjaxResult.data：新回复 |

分页每页1至50条，默认10条；内容去首尾空白后1至200字符。
作者和时间从服务端取得。普通评论接口忽略不在DTO中的额外作者/parentId字段，
构造出的普通评论parentId始终为null，不能借此绕过回复权限。
只允许回复本主题存在的顶层评论，不能回复回复。
异常消息由现有全局处理器包装，业务失败 `code` 不等于200。

## 7. 验证命令与限制

后端根目录：

```powershell
$env:JAVA_HOME = 'D:\develop\Java'
mvn.cmd -B -ntp -pl ruoyi-admin -am package
```

包含12个自动化测试：9个Service/参数校验测试，3个真实Spring方法权限测试。
测试不连接MySQL，Service测试替换Mapper，权限测试替换Service。
它们证明相应业务规则和方法权限代理有效，**不代替真实登录、数据库和HTTP联调**。

前端根目录：

```powershell
npm.cmd run build:prod
```

前端另有 `tests/forum-ui-smoke.cjs` 用于隔离的UI检查。
需要可用的Playwright模块，通过 `FORUM_PLAYWRIGHT_MODULE` 指向该模块，
并先启动前端开发服务。默认使用本机Edge无界面模式。
本次截图保存在任务的临时展示目录，不包含真实用户token。
UI检查中的假登录仅存在于测试拦截器，不是应用登录方式，不能据此宣称真实联调成功。

数据库管理员导入后，还要按下面检查：

- 未登录访问被拒绝，成员越权回复被拒绝，且未写入数据。
- 正常评论/回复落库，刷新读取正确。
- 空白/超长内容、无效目标、跨主题、回复回复均被拒绝。
- 使用伪造作者字段不能改变作者，普通评论夹带parentId不能产生回复。
- 页面按钮权限和真实接口权限一致，动态菜单可进入正确Vue页面。

## 常见问题

- 登录页验证码加载失败：检查后端是否启动，代理目标是否正确。
- 登录提示用户不存在：SQL未导入成功，不能仅凭文件存在认为账号已创建。
- 有账号但无菜单：核对角色关联、菜单component、权限标识，并重新登录。
- 提示表不存在：管理员需在后端实际连接的库中执行SQL。
- 权限拒绝：检查登录的是哪个账号；成员没有维护人员回复权限是预期行为。
- 数据库拒绝SELECT或INSERT：由管理员确认应用账号对新表的必要权限。

## 停止与回退

停止自己启动的前后端终端即可，不操作其他人的进程。
本次不修改既有阀井接口、系统安全规则、数据库账号权限或全局验证码开关。
若要停用演示账号/角色，可由管理员在若依管理页将它们停用；不要批量删除系统表。
