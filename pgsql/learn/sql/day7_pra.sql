-- 1. 先量化问题：129 个无效流域到底坏在哪
SELECT gid,
    ST_IsValidReason(geom) AS reason
FROM hydrobasins
WHERE NOT ST_IsValid(geom)
LIMIT 10;
-- 2. 清洗：生成有效几何副本列（不动原始数据）
ALTER TABLE hydrobasins
ADD COLUMN IF NOT EXISTS geom_valid geometry;
UPDATE hydrobasins
SET geom_valid = ST_MakeValid(geom);
---- 3. 统计
SELECT ST_GeometryType(geom) AS old_type,
    ST_GeometryType(geom_valid) AS new_type,
    COUNT(*)
FROM hydrobasins
WHERE NOT ST_IsValid(geom)
GROUP BY 1,
    2;
SELECT l.gid,
    l.name_zh,
    ST_Contains(b.geom_valid, l.geom) AS contains,
    ST_CoveredBy(l.geom, b.geom_valid) AS covered_by,
    ST_Intersects(b.geom_valid, l.geom) AS intersects
FROM hydrobasins b
    JOIN hydrolakes l ON ST_Intersects(b.geom_valid, l.geom)
WHERE b.gid = 746;
-- A. 太湖流域内的河流（ST_Intersects）
SELECT r.hyriv_id,
    r.ord_stra,
    ROUND(
        (ST_Length(r.geom::geography) / 1000)::numeric,
        1
    ) AS length_km
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
WHERE b.gid = 746
ORDER BY length_km DESC
LIMIT 20;
-- B. 口径解剖：ST_Intersects 捞出的是"相交"，包含"只擦边蹭进来一小段"的河。
--    用 ST_Crosses 细分"真正穿越边界"的河：
SELECT r.hyriv_id,
    ST_Intersects(b.geom_valid, r.geom) AS touches_basin,
    ST_Crosses(r.geom, b.geom_valid) AS crosses_border,
    ST_Within(r.geom, b.geom_valid) AS fully_inside
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
WHERE b.gid = 746
GROUP BY r.hyriv_id,
    b.geom_valid,
    r.geom
LIMIT 20;
-- C. 跨界河复现（Day 6 锚点 40005743）
SELECT r.hyriv_id,
    COUNT(DISTINCT b.gid) AS basin_cnt
FROM hydrorivers r
    JOIN hydrobasins b ON ST_Intersects(b.geom_valid, r.geom)
GROUP BY r.hyriv_id
ORDER BY basin_cnt DESC
LIMIT 5;
-- 河流沿岸10km范围内的湖泊
-- 1. 先挑一条有代表性的河（太湖流域内较长的）
SELECT r.gid,
    r.hyriv_id,
    ROUND(
        (ST_Length(r.geom::geography) / 1000)::numeric,
        1
    ) AS length_km
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom_valid, r.geom)
WHERE b.gid = 746
ORDER BY ST_Length(r.geom::geography) DESC
LIMIT 5;
-- 2. 沿岸 10km 湖泊清单 + 距离排序
SELECT l.gid,
    l.name_zh,
    ROUND((ST_Area(l.geom::geography) / 1e6)::numeric, 1) AS lake_area_km2,
    ROUND(
        (
            ST_Distance(l.geom::geography, r.geom::geography) / 1000
        )::numeric,
        2
    ) AS dist_km
FROM hydrorivers r
    JOIN hydrolakes l ON ST_DWithin(l.geom::geography, r.geom::geography, 10000)
WHERE r.gid = 637240
ORDER BY dist_km;
-- 找出全亚洲"一个湖都不含"的流域（LEFT JOIN 保留侧 + IS NULL）
SELECT b.gid,
    b.hybas_id,
    ROUND(
        (ST_Area(b.geom_valid::geography) / 1e6)::numeric,
        1
    ) AS basin_area_km2
FROM hydrobasins b
    LEFT JOIN hydrolakes l ON ST_CoveredBy(l.geom, b.geom_valid)
WHERE l.gid IS NULL
ORDER BY basin_area_km2 DESC
LIMIT 20;