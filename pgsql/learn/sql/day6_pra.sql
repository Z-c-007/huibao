-- 建表（延续路线 Day 6 数据，标注入库前先确认 test_polygon 等不存在）
DROP TABLE IF EXISTS test_polygon;
DROP TABLE IF EXISTS test_points;
CREATE TABLE test_polygon (geom geometry);
CREATE TABLE test_points (label VARCHAR, geom geometry);
INSERT INTO test_polygon
VALUES ('POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))');
INSERT INTO test_points
VALUES ('内部点', 'POINT(5 5)'),
    ('边界点', 'POINT(5 10)'),
    -- 注意：y=10 恰好落在上边线上
    ('外部点', 'POINT(15 5)');
-- 显式 CROSS JOIN：每个点 × 每个面 = 3 行（面只有一个，CROSS 等价逗号语法）
SELECT p.label,
    ST_Contains(t.geom, p.geom) AS "contains_面含点",
    ST_Within(p.geom, t.geom) AS "within_点在面内",
    ST_Covers(t.geom, p.geom) AS "covers_面覆盖点",
    ST_CoveredBy(p.geom, t.geom) AS "coveredby_点被覆盖",
    ST_Intersects(t.geom, p.geom) AS "intersects_相交",
    ST_Disjoint(t.geom, p.geom) AS "disjoint_相离",
    ST_DWithin(t.geom, p.geom, 1) AS "dwithin_距≤1",
    ST_Touches(t.geom, p.geom) AS "touches_接触"
FROM test_polygon t
    CROSS JOIN test_points p;
-- 线穿面：ST_Crosses 专用于"维度不对等"的穿越（线穿面、线穿线）
SELECT ST_Crosses(
        'LINESTRING(5 -5, 5 15)'::geometry,
        -- 竖直穿过面的线
        'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))'::geometry
    ) AS "线穿过面吗";
-- 面贴面：两个面只共享一条边，内部不重叠 → ST_Touches = t
SELECT ST_Touches(
        'POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))'::geometry,
        'POLYGON((5 0, 10 0, 10 5, 5 5, 5 0))'::geometry
    ) AS "两个面相切吗";
-- 面面部分重叠：ST_Overlaps（两面的交集面积 < 各自面积）
SELECT ST_Overlaps(
        'POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))'::geometry,
        'POLYGON((3 3, 8 3, 8 8, 3 8, 3 3))'::geometry
    ) AS "面面部分重叠吗";
-- 点相等：坐标完全相同
SELECT ST_Equals('POINT(5 5)'::geometry, 'POINT(5 5)'::geometry) AS "两点相等吗";
-- 场景：河长制岸线管控——距某条河道 5km 内的湖泊
-- 用合成数据演示语义：面内点、面外 1 单位内的点、面外远处的点
SELECT p.label,
    ST_DWithin(t.geom, p.geom, 1) AS "distance≤1",
    ST_DWithin(t.geom, p.geom, 20) AS "distance≤20"
FROM test_polygon t
    CROSS JOIN test_points p;
-- 注意：实测 hydrolakes 无 hylak_id，用 gid + name_zh
-- 太湖流域
SELECT l.gid,
    l.name_zh,
    ROUND((ST_Area(l.geom::geography) / 1e6)::numeric, 1) AS lake_area_km2
FROM hydrobasins b
    JOIN hydrolakes l ON ST_Contains(b.geom, l.geom)
WHERE b.gid = 746;
-- 用 ST_Intersects 找 "碰到流域" 的河流 （ 含跨界河 ， 见陷阱节 ）
SELECT COUNT(r.gid) AS river_cnt,
    ROUND((SUM(r.length_km))::numeric, 0) AS total_km
FROM hydrobasins b
    JOIN hydrorivers r ON ST_Intersects(b.geom, r.geom)
WHERE b.gid = 740;
-- 4.3 一条河跨几个流域？（重复计数的根源演示）
SELECT r.hyriv_id,
    COUNT(DISTINCT b.gid) AS basin_cnt
FROM hydrorivers r
    JOIN hydrobasins b ON ST_Intersects(b.geom, r.geom)
GROUP BY r.hyriv_id
ORDER BY 2 DESC
LIMIT 3;
-- 4.4 ST_DWithin + geography：距某条河 10km 内的湖泊
-- 先挑一条河：hyriv_id = 最长河流之一
SELECT r.hyriv_id,
    ROUND(
        (ST_Length(r.geom::geography) / 1000)::numeric,
        1
    ) AS length_km
FROM hydrorivers r
ORDER BY ST_Length(r.geom::geography) DESC
LIMIT 3;
SELECT l.gid,
    l.name_zh,
    ROUND(
        (
            ST_Distance(l.geom::geography, r.geom::geography) / 1000
        )::numeric,
        1
    ) AS dist_km
FROM hydrorivers r
    JOIN hydrolakes l ON ST_DWithin(l.geom::geography, r.geom::geography, 10000)
WHERE r.hyriv_id = 40005743
ORDER BY dist_km
LIMIT 5;