-- 认识几何类型
SELECT DISTINCT ST_GeometryType(geom)
FROM hydrorivers;
-- ｜看一条河长什么样
SELECT gid,
    ST_AsText(geom)
FROM hydrorivers
LIMIT 1;
-- 长度两种口径对比（字段 vs 现算）
SELECT gid,
    length_km,
    ROUND(ST_Length(geom::geography)::numeric / 1000, 2) AS calc_km
FROM hydrorivers
ORDER BY gid
LIMIT 3;
SELECT ST_Length(geom) AS deg,
    -- 度（无意义，数值极小）
    ST_Length(geom::geography) AS m -- 米（真实长度）
FROM hydrorivers
LIMIT 1;
-- 全亚洲水系总长
-- 错
SELECT ROUND(SUM(ST_Length(geom::geography)) / 1000, 1)
FROM hydrorivers;
-- 对
SELECT ROUND(
        (SUM(ST_Length(geom::geography)) / 1000)::numeric,
        0
    ) AS total_km
FROM hydrorivers;
-- 业务：水网金字塔 —— 高等级河段少但承担主干输水，1 级小支流占大头
SELECT ord_stra,
    COUNT(*) AS seg_cnt,
    ROUND(
        (SUM(ST_Length(geom::geography)) / 1000)::numeric,
        0
    ) AS len_km
FROM hydrorivers
GROUP BY ord_stra
ORDER BY ord_stra;
-- 业务：防洪调度重点 = 大流域；sub_area 已是 km²，直接排序即权威口径
SELECT gid,
    hybas_id,
    sub_area,
    up_area
FROM hydrobasins
ORDER BY sub_area DESC
LIMIT 5;
-- 对照（字段 vs 现算，验证"字段优先"）：
SELECT gid,
    sub_area,
    ROUND((ST_Area(geom::geography) / 1e6)::numeric, 1) AS calc_km2
FROM hydrobasins
WHERE gid IN (740, 1676)
ORDER BY gid;
-- 业务：湖泊库容评估；数据集没给面积，必须用 ST_Area 从几何现算
SELECT gid,
    name_zh,
    admin,
    ROUND((ST_Area(geom::geography) / 1e6)::numeric, 0) AS area_km2
FROM hydrolakes
WHERE name_zh IS NOT NULL
ORDER BY area_km2 DESC
LIMIT 5;
-- 业务：>5 万 km² 的大流域有几处（防洪重点关注面）
SELECT COUNT(*) AS big_basin_cnt
FROM hydrobasins
WHERE sub_area > 50000;
-- 与上一条等价，只是过滤条件直接写空间函数（路线文档 Day 4 自检题）
SELECT gid,
    hybas_id,
    ROUND((ST_Area(geom::geography) / 1e6)::numeric, 1) AS area_km2
FROM hydrobasins
WHERE ST_Area(geom::geography) / 1e6 > 1000
ORDER BY area_km2 DESC;