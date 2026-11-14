-- 省级河长打开系统，需要看到一份"流域档案卡"：
-- 每个流域里有多少条河、河流总长多少公里、湖泊覆盖面积占流域面积的比例。
-- 这些数据不是预先存好的，
-- 需要从 hydrorivers（142 万条河段）、hydrobasins（2489 个流域）、hydrolakes（1355 个湖泊）
-- 三张表中实时计算出来。
-- 找出太湖流域内所有河流
SELECT r.hyriv_id
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
WHERE b.gid = 746;
SELECT ROUND((ST_Length(geom::geography) / 1000)::numeric, 1) AS length_km
FROM hydrorivers
LIMIT 5;
SELECT ROUND((ST_Area(geom::geography) / 1e6)::numeric, 2) AS area_km2
FROM hydrobasins
LIMIT 5;
-- b.geom_valid必须写
SELECT b.hybas_id,
    COUNT(r.hyriv_id)
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
GROUP BY b.hybas_id,
    b.geom_valid;
-- 只保留河流数量 > 100 的流域
SELECT b.hybas_id,
    COUNT(r.hyriv_id) AS river_cnt
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
GROUP BY b.hybas_id
HAVING COUNT(r.hyriv_id) > 100;
-- 把河流裁剪到流域内部，只算流域内的那一段长度
SELECT ST_Length(
        ST_Intersection(r.geom, b.geom_valid)::geography
    ) / 1000 AS length_km
FROM hydrorivers r
    JOIN hydrobasins b ON ST_Intersects(b.geom_valid, r.geom)
WHERE b.gid = 746;
-- 练习 1：按流域统计河流数量 + 总长度（ST_Intersects + 聚合）
-- 业务需求：河长要一份报表，列出每个流域有多少条河段、河流总长多少公里，按总长度降序，只看前 20 名。
-- 预期输出：每个流域一条记录，含河流数量 + 总长度 km
-- ⚠️ 口径说明：ST_Intersects 会把跨多流域的河段完整计入每个流域，
--    总长度会虚高（跨界河段被重复计算），这是"快速浏览"口径。
--    精确口径见练习 1B（ST_Intersection 裁剪）。
SELECT b.gid,
    b.hybas_id,
    COUNT(r.hyriv_id) AS 河流数量,
    ROUND(
        SUM(ST_Length(r.geom::geography) / 1000)::numeric,
        1
    ) AS 河流总长_km
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
GROUP BY b.gid,
    b.hybas_id
ORDER BY 河流总长_km DESC
LIMIT 20;
-- 只算流域内部的那一段河流长度，不会重复计跨界河
SELECT b.gid,
    b.hybas_id,
    COUNT(r.hyriv_id) AS 河流数量,
    ROUND(
        SUM(
            ST_Length(ST_Intersection(r.geom, b.geom_valid)::geography) / 1000
        )::numeric,
        1
    ) AS 河流总长_km
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
GROUP BY b.gid,
    b.hybas_id
ORDER BY 河流总长_km DESC
LIMIT 20;
-- 练习 2：按流域统计湖泊面积占比（LEFT JOIN + COALESCE）
-- 业务需求 ： 河长想看每个流域里湖泊面积占流域面积的比例 ， 找出 "湖泊覆盖率" 最高的流域 。
-- 预期输出：每个流域的湖泊总面积、流域面积、湖泊覆盖率 %
-- ⚠️ 为什么用 LEFT JOIN：有些流域没有湖泊，用 LEFT JOIN 保留它们
--    而不是 INNER JOIN 把它们丢掉
SELECT b.gid,
    b.hybas_id,
    ROUND(
        (ST_Area(b.geom_valid::geography) / 1e6)::numeric,
        1
    ) AS 流域面积_km2,
    ROUND(
        (
            COALESCE(SUM(ST_Area(l.geom::geography)) / 1e6, 0)
        )::numeric,
        2
    ) AS 湖泊总面积_km2,
    ROUND(
        (
            100.0 * COALESCE(SUM(ST_Area(l.geom::geography)), 0) / ST_Area(b.geom_valid::geography)
        )::numeric,
        2
    ) AS 湖泊覆盖率
FROM hydrobasins b
    LEFT JOIN hydrolakes l ON ST_Intersects(b.geom_valid, l.geom)
GROUP BY b.gid,
    b.hybas_id,
    b.geom_valid
ORDER BY 流域面积_km2 DESC
LIMIT 20;
-- 练习 3：每条河流周围 5km 的湖泊数量（ST_DWithin + LEFT JOIN + 聚合）
-- 业务需求：防汛部门需要知道"每条河周围 5km 内有多少个湖泊"，用于评估洪水漫溢风险。只显示有湖泊的河流，按湖泊数量降序。
-- 预期输出：每条河一行，含附近湖泊数量 + 总面积
-- ⚠️ 单位：ST_DWithin 必须用 ::geography，否则 5000 是 5000 度
SELECT r.hyriv_id,
    r.ord_stra,
    COUNT(l.gid) AS 湖泊数量,
    ROUND(
        (
            COALESCE(SUM(ST_Area(l.geom::geography)) / 1e6, 0)
        )::numeric,
        2
    ) AS nearby_lake_area_km2
FROM hydrorivers r
    LEFT JOIN hydrolakes l ON ST_Intersects(ST_Expand(r.geom, 0.5), l.geom)
    AND ST_DWithin(r.geom::geography, l.geom::geography, 5000)
GROUP BY r.hyriv_id,
    r.ord_stra
HAVING COUNT(l.gid) > 0
ORDER BY 湖泊数量 DESC  
LIMIT 20;
-- 练习 4：三表空间连接（流域 → 河流 → 湖泊）
-- 业务需求：找一个具体流域（如太湖流域 gid=746），列出该流域内所有河流，以及每条河周围 5km 内的湖泊数量。
-- 预期输出：太湖流域内每条河一行，含河流长度 + 附近湖泊数量
-- 连接链：hydrobasins → hydrorivers（空间相交）→ hydrolakes（距离）
SELECT r.hyriv_id,
    r.ord_stra,
    ROUND(
        (ST_Length(r.geom::geography) / 1000)::numeric,
        1
    ) AS river_length_km,
    COUNT(l.gid) AS nearby_lake_count,
    ROUND(
        (
            COALESCE(SUM(ST_Area(l.geom::geography)) / 1e6, 0)
        )::numeric,
        2
    ) AS nearby_lake_area_km2
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
    LEFT JOIN hydrolakes l ON ST_Intersects(ST_Expand(r.geom, 0.5), l.geom)
    AND ST_DWithin(r.geom::geography, l.geom::geography, 5000)
WHERE b.gid = 746
GROUP BY r.hyriv_id,
    r.ord_stra,
    r.geom
ORDER BY nearby_lake_count DESC
LIMIT 20;
-- 练习 5：反向名单——没有河流穿过的流域（LEFT JOIN + IS NULL）
-- 业务需求 ： 找出 "一片荒芜" 的流域 — — 没有任何河流穿过 。 用于识别数据质量问题或特殊地理区域 。
-- 预期输出：没有任何河流的流域列表，按面积降序
-- ⚠️ 陷阱：谓词 ST_Intersects 必须写在 ON 里，不能写 WHERE
SELECT b.gid,
    b.hybas_id,
    ROUND(
        (ST_Area(b.geom_valid::geography) / 1e6)::numeric,
        1
    ) AS 流域面积_km2
FROM hydrobasins b
    LEFT JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
WHERE r.hyriv_id IS NULL
GROUP BY b.gid,
    b.hybas_id,
    b.geom_valid
ORDER BY 流域面积_km2 DESC
LIMIT 20;