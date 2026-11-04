package com.learning.approval.config;

import org.slf4j.*;
import org.springframework.boot.*;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/** 只读启动检查：缺少升级脚本或Redis无法认证时立即失败，不自动建表、不写业务数据。 */
@Component
public class DependencyReadinessVerifier implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DependencyReadinessVerifier.class);
    private final JdbcTemplate jdbc;
    private final StringRedisTemplate redis;

    public DependencyReadinessVerifier(JdbcTemplate jdbc, StringRedisTemplate redis) {
        this.jdbc = jdbc;
        this.redis = redis;
    }

    @Override
    public void run(ApplicationArguments args) {
        try {
            Integer installed = jdbc.queryForObject(
                "SELECT COUNT(*) FROM app_schema_version WHERE version='2'",
                Integer.class
            );
            if (installed == null || installed != 1) throw new IllegalStateException(
                "尚未完成V2 SQL升级"
            );
            // 不只相信版本标记：也核对本轮必须增加的列，避免手动脚本中途出错后继续执行。
            Integer columns = jdbc.queryForObject(
                """
                SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND (
                  (table_name='project' AND column_name='deleted') OR
                  (table_name='approval_step' AND column_name IN ('started_at','actor_name','org_name')) OR
                  (table_name='approval_assignee' AND column_name IN ('username','display_name')) OR
                  (table_name='project_event' AND column_name IN ('round_no','step_id','actor_name','before_status','after_status','before_version','after_version')))
                """,
                Integer.class
            );
            if (columns == null || columns != 13) throw new IllegalStateException(
                "V2所需业务字段尚未完整建立"
            );
        } catch (RuntimeException e) {
            throw new IllegalStateException(
                "数据库未准备好：请在project_approval_demo执行sql/upgrade_v1_to_v2.sql，并核对连接密码",
                e
            );
        }
        try (var connection = redis.getConnectionFactory().getConnection()) {
            if (!"PONG".equals(connection.ping())) throw new IllegalStateException(
                "Redis未返回PONG"
            );
        } catch (RuntimeException e) {
            throw new IllegalStateException(
                "Redis连接失败：请检查Memurai服务、APP_REDIS_PASSWORD和Redis连接配置",
                e
            );
        }
        log.info("依赖检查完成：MySQL V2结构、Redis连接可用；启动过程未执行建表或业务写入");
    }
}
