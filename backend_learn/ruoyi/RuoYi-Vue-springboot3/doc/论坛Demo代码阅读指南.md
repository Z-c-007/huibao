# 从“发表评论”学习一条完整请求

> 编辑、删除与Redis登录链路见同目录《论坛CRUD与Redis讲解.md》，本文保留新增操作的阅读顺序。

先完成运行手册中的数据库初始化和登录，再从页面操作追踪下面的文件。
这是一条写数据库的链路，比原阀井只读查询多了参数校验、真实用户身份与权限。

## 1. 页面收集内容

前端 `src/views/forum/discussion/index.vue`，找 `submitComment()`。
输入经前端trim与长度校验后，构造 `{ topicId, content }`。
这时它是浏览器中的JavaScript对象，页面没有发送作者ID或角色。

## 2. API和请求封装

前端 `src/api/forum/discussion.js`，找 `addComment(data)`。
它调用现有 `@/utils/request`，请求 `POST /forum/comments`。
开发环境会加 `/dev-api` 前缀，Vite再把它代理到后端。
现有请求封装负责携带Bearer token、解析若依业务错误和处理登录失效。

## 3. 请求进入后端

Tomcat接收HTTP，现有过滤器链处理登录身份与认证，Spring MVC匹配Controller方法。
`ruoyi-admin/src/main/java/com/ruoyi/web/controller/forum/ForumController.java`：

- 类路径 `/forum` + 方法路径 `/comments`，并匹配POST。
- `@PreAuthorize` 检查当前用户的 `forum:comment:add`。
- `@RequestBody` 将JSON转成请求对象。
- `@Validated` 校验请求对象，失败交给现有异常处理器。
- `@Log` 沿用若依操作日志机制。

方法权限是进入业务前的检查；前端隐藏按钮不能替代它。

## 4. 请求对象只接收允许修改的字段

`ruoyi-system/src/main/java/com/ruoyi/system/domain/dto/ForumCommentRequest.java`。
DTO意为数据传输对象，这里专门表示“新增评论的输入”。
topicId必须是正数，content去除首尾空白后非空且不超过200字符。
与数据库实体分开，避免直接接受作者、创建时间等敏感字段。
`ForumReplyRequest` 继承这个类，再增加必需的parentId。

## 5. Service声明与实现

`service/IForumService.java` 声明能力，没有相应业务方法体。
`service/impl/ForumServiceImpl.java` 才是具体实现；Spring将实现注入Controller。
接口与Impl共同属于Service层，不是请求额外经过两个业务层。

找 `addComment()` → `save()`：

1. 验证主题存在。
2. 普通评论parentId由服务端固定为null。
3. 再检查关键内容规则。
4. `SecurityUtils.getLoginUser()` 取得当前真实用户。
5. 构造ForumComment，填写真实作者、创建时间和内容。
6. 调用Mapper插入。

`addReply()` 还通过 `requireRootComment()` 校验目标存在、同主题、顶层评论。
本模块没有删除入口，每次新增只有一次数据库写入，没有人为添加复杂事务。

## 6. Mapper连接SQL

`mapper/ForumMapper.java` 声明 `insertComment(ForumComment comment)`。
`resources/mapper/system/ForumMapper.xml`：

- namespace关联Mapper完整接口名称。
- insert的id关联insertComment方法名。
- `#{...}` 绑定参数。
- `useGeneratedKeys`、`keyProperty` 将数据库生成的commentId回填对象。

MyBatis借助连接池与驱动访问MySQL；数据库真的新增一行，不是页面临时保存。

## 7. 数据对象与响应

`domain/ForumComment.java` 描述保存和返回的数据，不是SQL调用的下一站。
一行记录对应一个对象，多行查询结果对应List。
`BaseEntity` 提供创建者、创建时间等公共属性及时间序列化格式。

新增对象返回Controller，通过 `success(...)` 包装成code/msg/data。
Spring MVC配合Jackson写成JSON；前端收到成功后清空输入并重新查第一页评论。
列表是 `rows/total`，新增和详情是 `data`，页面API读取需按契约区分。

## 8. 用回复请求理解权限

成员与维护人员都可评论，但只有维护人员有 `forum:reply:add`。
Vue的 `v-hasPermi` 控制显示，Controller的 `@PreAuthorize` 实施服务端限制。
攻击者即使显示按钮、直接发请求或伪造角色字段，也不会改变真实登录权限。
身份由token恢复，权限来自用户角色菜单关系，作者来自后端安全上下文。

本例演示功能权限与目标合法性，不演示“用户只能编辑自己的评论”，因为没有编辑删除接口。

## 推荐每次学习一小段

1. 操作页面，观察Network中的请求与响应。
2. Controller断点观察DTO。
3. Service断点观察登录用户与构造的实体。
4. SQL日志和数据库中查看新增行。
5. 用成员身份尝试回复，观察为什么没有进入Service。
6. 小改动练习：修改内容上限时同步前后端、表字段与测试，不只改页面。
