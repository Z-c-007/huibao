-- w10_00_explain.sql ｜ Day 12 Step A：EXPLAIN ANALYZE 验证 GiST 索引命中（Day 10 伏笔清算）
-- 前置：VSCode 扩展连接切到【开发库 ai_water_budget】（不是测试库！）
-- 执行方式：逐段选中执行，对照各段注释里的预期
-- 性质：只读诊断脚本，不改任何数据、不动 tools.py
-- 结论落点：笔记 11（当前规模是否需要"表达式索引"）
--
-- 【如何读执行计划 · 60 秒指南】
--   缩进：从最里层节点往外读 = 执行顺序
--   节点名：Seq Scan = 全表逐行扫（无索引）
--           Index Scan / Bitmap Index Scan = 走索引（后者 = 先索引定位再回表）
--   actual time=..rows=..：真实耗时与真实行数（ANALYZE 实跑才有）
--   Rows Removed by Filter：扫了但被 WHERE 淘汰的行数（大 = 扫描低效的信号）
--   cost=启动成本..总成本：估算值（单位随意），用于节点间比较
-- ===== 段 1 ｜ find_nearby 原查询（::geography 口径）=====
-- 预期：两侧都是 Seq Scan（rivers 868 行全扫；water_users 仅 4 行直接扫）
--   注意 ON 条件里的 geom::geography——谓词用了转换表达式，geometry 的 GiST 索引不匹配它
--   预期结果：1 行（顺义某农场，约 4.76）——和 Day 11 工具输出一致
EXPLAIN ANALYZE
SELECT u.name,
    u.industry,
    u.water_used,
    u.budget,
    ROUND(
        (
            MIN(
                ST_Distance(u.geom::geography, r.geom::geography)
            ) / 1000.0
        )::numeric,
        2
    ) AS distance_km
FROM water_users u
    JOIN rivers r ON ST_DWithin(u.geom::geography, r.geom::geography, 5000)
    AND r.name = '潮白河'
GROUP BY u.id,
    u.name,
    u.industry,
    u.water_used,
    u.budget
ORDER BY distance_km;
-- ===== 段 2a ｜ 对照组：geometry 口径（让优化器自己选）=====
-- 预期：很可能仍是 Seq Scan！
--   原因：water_users 只有 4 行，优化器算下来"顺序扫 4 行"比"先查索引再回表"更便宜
--   这本身是知识点：索引在 ≠ 一定用，小表上优化器会主动放弃索引
--   预期结果：1 行（顺义某农场）
EXPLAIN ANALYZE
SELECT u.name
FROM water_users u
WHERE ST_DWithin(
        u.geom,
        ST_SetSRID(ST_MakePoint(116.78, 40.12), 4326),
        0.05
    );
-- ===== 段 2b ｜ 强制走索引（验证索引存在且可用）=====
-- SET enable_seqscan = off：会话级开关，禁止优化器选 Seq Scan（教学演示用，生产慎用）
-- 预期：Bitmap Index Scan on water_users_geom_gix + Bitmap Heap Scan（回表）
--   ——亲眼看到"索引命中的样子"；geometry 口径谓词与 GiST 索引类型匹配
-- 最后一段把开关拨回来，避免影响后续查询
SET enable_seqscan = off;
EXPLAIN ANALYZE
SELECT u.name
FROM water_users u
WHERE ST_DWithin(
        u.geom,
        ST_SetSRID(ST_MakePoint(116.78, 40.12), 4326),
        0.05
    );
SET enable_seqscan = on;
-- ===== 段 3 ｜ 索引清单 =====
-- 预期：12 行 = 每表 3 个（pkey 主键 + unique 唯一约束 + geom_gix GiST 空间索引）
--   重点看 4 条 indexdef 含 USING gist (geom)
SELECT tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('districts', 'streets', 'rivers', 'water_users')
ORDER BY tablename,
    indexname;
-- ===== 附 ｜ 将来的解法预览（今天不执行，仅语法存档）=====
-- 数据到百万行级、geography 口径查询成为主力时，建"表达式索引"让转换结果本身进索引：
-- CREATE INDEX water_users_geom_geog_gix ON water_users USING GIST ((geom::geography));
-- CREATE INDEX rivers_geom_geog_gix      ON rivers      USING GIST ((geom::geography));
-- 建后段 1 的计划将变为 Bitmap Index Scan——这是笔记 11 的标准结论