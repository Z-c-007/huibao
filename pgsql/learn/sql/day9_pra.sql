DROP TABLE IF EXISTS test_rivers,
test_lakes,
test_basins;
CREATE TABLE test_rivers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(30),
    geom geometry(LineString, 4326)
);
CREATE TABLE test_lakes (
    id SERIAL PRIMARY KEY,
    lake_name VARCHAR(30),
    geom geometry(Polygon, 4326)
);
CREATE TABLE test_basins (
    id SERIAL PRIMARY KEY,
    basin_name VARCHAR(30),
    geom geometry(Polygon, 4326)
);
-- 三条河：永定河(西)、潮河(东)、拒马河(很远，无湖)
INSERT INTO test_rivers (name, geom)
VALUES (
        '永定河示例',
        ST_GeomFromText('LINESTRING(116.0 40.0, 116.5 40.0)', 4326)
    ),
    (
        '潮河示例',
        ST_GeomFromText('LINESTRING(117.0 39.8, 117.5 39.8)', 4326)
    ),
    (
        '拒马河示例',
        ST_GeomFromText('LINESTRING(115.0 39.0, 115.5 39.0)', 4326)
    );
-- 四个小湖：水库A 挨着永定河；水库C、D 挨着潮河；水库B 是"孤儿"（离任何河都 >5km）
INSERT INTO test_lakes (lake_name, geom)
VALUES (
        '水库A',
        ST_GeomFromText(
            'POLYGON((116.14 40.01, 116.16 40.01, 116.16 40.03, 116.14 40.03, 116.14 40.01))',
            4326
        )
    ),
    (
        '水库B',
        ST_GeomFromText(
            'POLYGON((116.69 40.00, 116.71 40.00, 116.71 40.02, 116.69 40.02, 116.69 40.00))',
            4326
        )
    ),
    (
        '水库C',
        ST_GeomFromText(
            'POLYGON((117.09 39.81, 117.11 39.81, 117.11 39.83, 117.09 39.83, 117.09 39.81))',
            4326
        )
    ),
    (
        '水库D',
        ST_GeomFromText(
            'POLYGON((117.24 39.80, 117.26 39.80, 117.26 39.82, 117.24 39.82, 117.24 39.80))',
            4326
        )
    );
INSERT INTO test_basins (basin_name, geom)
VALUES (
        '示例流域',
        ST_GeomFromText(
            'POLYGON((115.5 39.5, 117.5 39.5, 117.5 40.2, 115.5 40.2, 115.5 39.5))',
            4326
        )
    );
-- 核心查询：每条河 5km 内的湖泊数量与总面积（LEFT JOIN 保留无湖的河）
-- 业务：河长制档案。以河流为主体，LEFT JOIN 湖泊，按河分组聚合。
SELECT r.name,
    COUNT(l.id) AS lake_count,
    ROUND(
        (
            COALESCE(SUM(ST_Area(l.geom::geography)), 0) / 1e6
        )::numeric,
        2
    ) AS lake_area
FROM test_rivers r
    LEFT JOIN test_lakes l ON ST_DWithin(l.geom::geography, r.geom::geography, 5000)
GROUP BY r.id,
    r.name
HAVING COUNT(l.id) > 0 -- 分组后过滤：排除无湖的河
ORDER BY lake_count DESC;
-- 核心查询：三表连接 流域 → 河流 → 湖泊（重点看 fan-out 陷阱）
-- 业务：某流域内，列出每条河以及它附近的湖数量、该河自身长度
SELECT r.name AS river_name,
    COUNT(l.id) AS lake_count,
    ROUND(
        (ST_Length(r.geom::geography) / 1000)::numeric,
        1
    ) AS river_length_km
FROM test_basins b
    JOIN test_rivers r ON ST_Intersects(r.geom, b.geom)
    LEFT JOIN test_lakes l ON ST_DWithin(l.geom::geography, r.geom::geography, 5000)
GROUP BY r.id,
    r.name
ORDER BY lake_count DESC;