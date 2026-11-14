-- 业务方：市水务局河湖管理处 + 国土空间规划科。要出一份"流域生态管控一张图(举例用b.gid = 611)"：
-- 1. 流域内每个湖多大、该按什么级别管控？（清单 + 分档）
-- 2. 流域内所有河的 5km 生态缓冲带合并成"连续管控区"，总面积多少？（合并去重）
-- 3. 管控区压到了哪些湖？各压了多大？（重叠量算）
-- 4. 管控区减去城镇建成区后，剩多少"可调整生态空间"？每个湖的质心在哪挂名？（扣减 + 取心）
-- 5. 最终结果以 GeoJSON 交给前端渲染（接 Day 16）。
--练习1
SELECT b.gid,
    COALESCE(NULLIF(l.name_zh, ''), l.name) AS lake_name,
    l.gid,
    ROUND((ST_Area(l.geom::geography) / 1e6)::numeric, 1) AS area_km2,
    -- 强制项#1：ROUND 先 ::numeric
    CASE
        WHEN ST_Area(l.geom::geography) / 1e6 > 100 THEN '大型' -- 分档阈值
        WHEN ST_Area(l.geom::geography) / 1e6 > 10 THEN '中型'
        ELSE '小型'
    END AS size_category
FROM hydrolakes l
    JOIN hydrobasins b ON ST_Contains(b.geom, l.geom)
WHERE b.gid = 611
ORDER BY area_km2 DESC;
--练习2 流域内所有河的 5km 生态缓冲带合并成"连续管控区"，总面积多少？（合并去重）
WITH basin_rivers AS (
    SELECT r.gid,
        r.geom
    FROM hydrorivers r
        JOIN hydrobasins b ON ST_Contains(b.geom, r.geom) -- 圈流域内，显式 JOIN
    WHERE b.gid = 611
)
SELECT COUNT(*) AS river_count,
    -- 参与河流数
    ROUND(
        (
            ST_Area(
                ST_Union(
                    -- ④ 聚合：N 条 → 1 张面（重叠溶解）
                    ST_Buffer(br.geom::geography, 5000)::geometry -- ③ 米制缓冲 → 转回 geometry
                )::geography -- ⑤ 结果转球面
            ) / 1e6
        )::numeric,
        2
    ) AS control_zone_km2
FROM basin_rivers br;
--练习3
WITH control_zone AS (
    -- ① 先把题 2 的"连续管控区"当一张临时表
    SELECT ST_Union(ST_Buffer(r.geom::geography, 5000)::geometry) AS geom
    FROM hydrorivers r
        JOIN hydrobasins b ON ST_Contains(b.geom, r.geom)
    WHERE b.gid = 611
)
SELECT l.gid,
    COALESCE(NULLIF(l.name_zh, ''), l.name) AS lake_name,
    ROUND(
        (
            ST_Area(
                ST_Intersection(cz.geom, l.geom)::geography -- ④ 精确量"重叠那块"的面积
            ) / 1e6
        )::numeric,
        3
    ) AS overlap_km2
FROM control_zone cz
    JOIN hydrolakes l ON ST_Intersects(cz.geom, l.geom) -- ② 把湖和管控区"叠图"，只留碰到的
ORDER BY overlap_km2 DESC;
--练习4
-- ④a 用 ST_MakeEnvelope 造一个"城镇建成区"矩形（覆盖洪湖一带），从管控区里扣掉
WITH control_zone AS (
    SELECT ST_Union(ST_Buffer(r.geom::geography, 5000)::geometry) AS geom
    FROM hydrorivers r
        JOIN hydrobasins b ON ST_Contains(b.geom, r.geom)
    WHERE b.gid = 611
)
SELECT ROUND(
        (
            ST_Area(
                -- ⑥ 量剩余面积
                ST_Difference(
                    cz.geom,
                    -- ⑤ 管控区 减 建成区
                    ST_MakeEnvelope(113.0, 29.5, 113.7, 30.2, 4326) -- ③ 矩形（第 5 参 srid=4326 必写！）
                )::geography
            ) / 1e6
        )::numeric,
        2
    ) AS adjustable_km2
FROM control_zone cz;
-- ④b 每个湖的质心，用于地图挂名挂牌
SELECT l.gid,
    COALESCE(NULLIF(l.name_zh, ''), l.name) AS lake_name,
    ST_AsText(ST_Centroid(l.geom)) AS centroid_wkt,
    ROUND((ST_Area(l.geom::geography) / 1e6)::numeric, 1) AS area_km2
FROM hydrolakes l
    JOIN hydrobasins b ON ST_Contains(b.geom, l.geom)
WHERE b.gid = 611
ORDER BY area_km2 DESC;