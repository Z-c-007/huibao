# 反馈讨论区

官方若依 Vue3 前端3.9.2，源码与本地改动说明见 `UPSTREAM.md`。

1. 先阅读相邻后端 `RuoYi-Vue-springboot3/doc/论坛Demo运行与演示.md`。
2. 本机数据库管理员在 `ry-vue` 执行后端的 `sql/forum_demo.sql`。
3. 启动后端，默认8080，MySQL与Redis/Memurai可用。
4. 本目录 `npm.cmd ci --no-audit --no-fund`（已装依赖可跳过）。
5. `npm.cmd run dev`，访问 http://127.0.0.1:5173/login?redirect=/forum/discussion 。
6. 使用运行手册中的本地演示账号登录，输入真实验证码。

页面：`src/views/forum/discussion/index.vue`。
API：`src/api/forum/discussion.js`。
构建：`npm.cmd run build:prod`。
不需要阀井示例的 valve-well-demo Profile，不关闭登录或验证码。

当前数据库尚未导入，真实账号与评论落库联调待完成；请勿将代码构建成功当成业务已验证。
