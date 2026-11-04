# 本轮检查记录

本轮仅做源码和构建检查，没有连接数据库、执行 SQL、启动后端或进行真实登录测试。

- 后端：JDK 17、Maven `clean compile`，跳过测试；重新编译 67 个 Java 文件，清理旧版平铺类的构建产物。
- 前端：`npm run build`，Vue/Vite 生产构建通过，22 个模块。
- 静态检查：5 个 MyBatis XML 能解析，namespace 对应 Java Mapper 接口，SQL 语句 id 对应接口方法。
- SQL：已检查脚本结构及格式化前后 SQL 词法内容一致；这不等于已在 MySQL 执行成功。

数据库升级、Redis 配置、IDEA 启动及真实业务验收由你操作。已有 V1 数据库使用 `sql/upgrade_v1_to_v2.sql`；具体步骤见 README，验收场景见 `docs/MANUAL_ACCEPTANCE.md`。

构建成功不能证明权限、并发、迁移和历史数据行为已通过实际验证。完成本机联调后，再按实际结果补充验收记录。
