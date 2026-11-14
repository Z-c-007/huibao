CREATE TABLE geometries (name VARCHAR, geom geometry);
INSERT INTO geometries
VALUES ('点', 'POINT(116.4 39.9)'),
    ('多点', 'MULTIPOINT(116.4 39.9, 121.5 31.2)'),
    ('线', 'LINESTRING(116 39, 117 40, 118 39)'),
    (
        '多线',
        'MULTILINESTRING((116 39, 117 40),(118 39, 119 40))'
    ),
    (
        '面',
        'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))'
    ),
    (
        '带洞面',
        'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0),(3 3, 3 7, 7 7, 7 3, 3 3))'
    ),
    (
        '多面',
        'MULTIPOLYGON(((0 0,5 0,5 5,0 5,0 0)),((6 6,9 6,9 9,6 9,6 6)))'
    ),
    (
        '集合',
        'GEOMETRYCOLLECTION(POINT(0 0), LINESTRING(1 1, 2 2))'
    );
SELECT *
FROM geometries;
SELECT name,
    ST_GeometryType(geom),
    ST_NDims(geom),
    ST_SRID(geom),
    ST_NumGeometries(geom)
FROM geometries;
-- 类型闸门
SELECT ST_GeometryType(geom),
    ST_NDims(geom),
    ST_SRID(geom)
FROM hydrorivers
LIMIT 1;
-- ① 全库成员数分布 ST_NumGeometries是子几何的数量，Multi*/集合里有几个成员？单件返回 1
SELECT ST_NumGeometries(geom) AS 成员数,
    COUNT(*) AS 行数
FROM hydrorivers
GROUP BY 1
ORDER BY 1;
-- ② 流域的多部件分布（2306 个单部件，最多 13 个部件）
SELECT ST_NumGeometries(geom) AS 部件数,
    COUNT(*) AS 条数
FROM hydrobasins
GROUP BY 1
ORDER BY 1 DESC
LIMIT 5;
-- ③ 带洞流域：外环 vs 内环（gid=1475 有 16 个洞）
SELECT gid,
    ST_AsText(ST_ExteriorRing(ST_GeometryN(geom, 1))) AS 外环,
    ST_NumInteriorRings(ST_GeometryN(geom, 1)) AS 洞数
FROM hydrobasins
WHERE ST_NumGeometries(geom) >= 2
LIMIT 10;
-- ④ ST_Dump 把 Multi 炸成多行（Day 8-9 空间聚合的基础）
SELECT gid,
    (ST_Dump(geom)).path AS 部件序号,
    ST_AsText((ST_Dump(geom)).geom) AS 部件
FROM hydrobasins
WHERE ST_NumGeometries(geom) >= 2
LIMIT 4;
-- 129 个流域边界自相交！这才是真实 shp 的真相
SELECT COUNT(*) AS 无效数
FROM hydrobasins
WHERE ST_IsValid(geom) = false;
-- 看坏在哪（ST_IsValidReason 返回原因文本）
SELECT gid,
    ST_IsValidReason(geom)
FROM hydrobasins
WHERE ST_IsValid(geom) = false
LIMIT 5;
-- 修复（ST_MakeValid，PostGIS 内置清洗器，此处只演示说明）
SELECT gid,
    ST_IsValid(ST_MakeValid(geom)) AS 修复后
FROM hydrobasins
WHERE ST_IsValid(geom) = false
LIMIT 5;
-- ST_AsGeoJSON(geometry) → text，坐标 [经度, 纬度]，单位=原坐标系(度)
SELECT ST_AsGeoJSON(geom)
FROM hydrorivers
LIMIT 1;