-- 河长制平台"河流健康档案"汇总接口
-- 业务方是水利局信息中心。
-- 他们的移动端大屏要展示一份全国水系统计：选择一个"矩形取景框"（地图框选），
-- 立刻返回框内 142 万条河段里命中多少条、总长多少。
-- 业务方的要求就一句：*"框选出结果要 1 秒内出，谁慢了谁挨批。"*
-- 问题是：框选 API 每次请求都要在一张 143 万行、336MB 的表上做包含/相交判断。
-- 如果没有索引，PostgreSQL 只能一行一行地读整张表、把每一条河的几何都拿出来跟取景框做一次精确相交计算——这就是 Seq Scan（全表扫描）。
-- 而真正的做法是：
-- 1. 先粗筛：每条河在数据库里只登记一个"外接矩形"（bbox）。
-- 判断"取景框 bbox 与河 bbox 有没有重叠"（&&），这一步不需要看几何细节，走索引，几毫秒内只捞出"可能命中"的那几百条。
-- 2. 再精算：只对这几百条候选做精确相交，返回真正结果。
-- 为什么前端 / 中间件做不到？ 浏览器不可能容纳 143 万条河段（下载就是几百 MB）；
-- 就算分页拉，每次也要和数据库重复做全集比较。
-- 真正的省钱方式是在数据库里把"全集比较"变成"索引定位"。
-- 这也决定了后面 tippecanoe/martin → 矢量瓦片 管线里，"空间索引"是性能底线——没有它，瓦片引擎也是挪不动的。
-- 业务：上线前先问"数据到底有没有索引"，防止拍到空手
-- 练习
SELECT tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('hydrorivers', 'hydrobasins', 'hydrolakes')
ORDER BY tablename;
-- 业务：教学需要一张"没索引的正交实验台"，不许动线上 143 万行真表
CREATE TABLE teach_rivers AS
SELECT gid,
    ord_stra,
    geom
FROM hydrorivers
WHERE ST_Intersects(geom, ST_MakeEnvelope(100, 20, 130, 45, 4326)) -- 只抽东亚范围
LIMIT 100000;
-- 业务：接口上线前用 EXPLAIN 体检——这是"有任何索引之前"的预报
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM teach_rivers
WHERE ST_Intersects(geom, ST_MakeEnvelope(120, 31, 121, 32, 4326));
-- 业务：给教学表加上空间索引
CREATE INDEX teach_rivers_geom_idx ON teach_rivers USING GIST (geom);
SELECT *
FROM teach_rivers;
-- 业务：框选 API 的主体查询。143 万行上直接跑，验证走索引后的真实耗时
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM hydrorivers
WHERE ST_Intersects(geom, ST_MakeEnvelope(120, 31, 121, 32, 4326));
-- 业务：档案卡，Day 8 用过的同一查询，今天看它的完整执行路径
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom, r.geom)
WHERE b.gid = 746;
-- ✅ 正确边：ST_Expand 放在驱动侧，让被探测列 l.geom 裸着
EXPLAIN
SELECT r.gid
FROM hydrorivers r
    LEFT JOIN hydrolakes l ON ST_Intersects(ST_Expand(r.geom, 0.5), l.geom)
    AND ST_DWithin(l.geom::geography, r.geom::geography, 5000)
WHERE r.gid = 100;
-- ✅ 推荐：geometry bbox 粗筛（走 GiST）+ geography 精算（米制）
SELECT COUNT(*)
FROM hydrorivers r
    JOIN (
        SELECT ST_SetSRID(ST_MakePoint(120, 31), 4326)::geometry AS pt
    ) c ON true
WHERE ST_Intersects(r.geom, ST_Expand(c.pt, 0.5)) -- 粗筛，走 hydrorivers_geom_idx
    AND ST_DWithin(r.geom::geography, c.pt::geography, 50000);