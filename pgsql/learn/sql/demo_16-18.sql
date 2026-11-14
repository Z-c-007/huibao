-- 业务方：市水务局河湖管理处。
-- 要一份「流域生态管控一张图」
-- 把一个流域的水系、湖泊、5km 生态管控区、被管控区压到的湖、湖名挂标全部渲染到一张 Web 地图上。
--------first_step----------
-- ：处长问「你管哪个流域？」你不能随便挑。
-- 你要做的：先按面积把全库流域从大到小排一遍（demo_16-18.sql 第 4-9 行），
-- 挑一个面积大、有代表性的（gid=611）。
-- 然后再盘点一下（第 10-22 行）：这个流域里有几条河、几个湖——确认数据量够，免得画出来是张空图。
-- → 一句话：先选地盘，再盘点地盘里有什么。
SELECT b.gid,
    ROUND((ST_Area(b.geom::geography) / 1e6)::numeric, 2) AS area_km2
FROM hydrobasins b
ORDER BY area_km2 DESC
LIMIT 20;
-- 确认 gid=611 流域内有多少河、多少湖（粗看数据量）
SELECT (
        SELECT COUNT(*)
        FROM hydrorivers r
            JOIN hydrobasins b ON ST_Contains(b.geom, r.geom)
        WHERE b.gid = 611
    ) AS river_cnt,
    (
        SELECT COUNT(*)
        FROM hydrolakes l
            JOIN hydrobasins b ON ST_Contains(b.geom, l.geom)
        WHERE b.gid = 611
    ) AS lake_cnt;
-------second_step----------
-- 业务问题：D 图层「5km 管控区」= 流域里每条河各自向外扩 5km，再把几百张缓冲面带重叠部分合并成一张大绿面。
-- 这个计算要跑很久，而且后面 E、G 都要用它。
-- 你要做的：算一次，存成一张表（CREATE TABLE ... AS）+ 建 GiST 索引，以后查表就行，不用每次重算。
-- → 一句话：像写代码把重复用的复杂结果存进变量，而不是每次重算（这也是将来接 GeoServer 时每个图层对应一张表）。
DROP TABLE IF EXISTS demo_basin_rivers;
CREATE TABLE demo_basin_rivers AS
SELECT r.gid,
    r.hyriv_id,
    r.main_riv,
    r.geom
FROM hydrorivers r
    JOIN hydrobasins b ON ST_Contains(b.geom, r.geom)
WHERE b.gid = 611;
CREATE INDEX demo_basin_rivers_geom_gix ON demo_basin_rivers USING GIST (geom);
SELECT *
FROM demo_basin_rivers
LIMIT 5;
--业务：法规要求每条河两岸各 5km 不准乱开发。但河很多，各自的 5km 缓冲带会互相重叠——简单相加会重复计数。
-- 所以要先把每条河扩 5km，再把几百张带重叠的面合并溶解成一张连续的大绿面，这才是「管控区」的真实总面积。
CREATE TABLE demo_control_zone AS
SELECT 1 AS id,
    ST_Union(ST_Buffer(r.geom::geography, 5000)::geometry) AS geom
FROM demo_basin_rivers r;
CREATE INDEX demo_control_zone_geom_gix ON demo_control_zone USING GIST (geom);
SELECT *
FROM demo_control_zone;
-- 业务：拿 M2 那张大绿面去「压」全库的湖泊，回答两个问题：
-- ①哪些湖被管控区覆盖到了（受法规限制）？
-- ②各压了多少面积（限制程度）——全覆盖=严管，擦边=轻度影响。
CREATE TABLE demo_lake_overlay AS
SELECT l.gid,
    COALESCE(NULLIF(l.name_zh, ''), l.name) AS lake_name,
    ROUND((ST_Area(l.geom::geography) / 1e6)::numeric, 1) AS lake_area_km2,
    ROUND(
        (
            ST_Area(ST_Intersection(cz.geom, l.geom)::geography) / 1e6
        )::numeric,
        3
    ) AS overlap_km2
FROM demo_control_zone cz
    JOIN hydrolakes l ON ST_Intersects(cz.geom, l.geom)
ORDER BY overlap_km2 DESC;
SELECT *
FROM demo_lake_overlay;
-- 查询 A：流域边界（地图第 1 层 · 灰色范围框）
-- 业务：给领导画「管的范围在哪」。整图最底层的一个淡灰半透明框，框内=职责范围。
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(geom)::jsonb,
                'properties',
                jsonb_build_object(
                    'gid',
                    gid,
                    'area_km2',
                    ROUND((ST_Area(geom::geography) / 1e6)::numeric, 1)
                )
            )
        )
    ) AS geojson
FROM hydrobasins
WHERE gid = 611;
-- 查询 B：流域内河流（地图第 2 层 · 蓝色线）
-- 业务：把 M1 物化表里的河画成线，附上干流名 + 长度——领导能看出「这片水系的骨架」。
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(geom)::jsonb,
                'properties',
                jsonb_build_object(
                    'gid',
                    gid,
                    'hyriv_id',
                    hyriv_id,
                    'main_riv',
                    main_riv,
                    'length_km',
                    ROUND((ST_Length(geom::geography) / 1000)::numeric, 1)
                )
            )
        )
    ) AS geojson
FROM demo_basin_rivers;
-- 查询 C：流域内湖泊 + 面积分档（地图第 3 层 · 三色面）
-- 业务：把湖画出来，并按面积分档着色——红=大型（管控最严）、橙=中型、蓝=小型。领导一眼看出哪些湖是重点。
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(l.geom)::jsonb,
                'properties',
                jsonb_build_object(
                    'gid',
                    l.gid,
                    'lake_name',
                    COALESCE(NULLIF(l.name_zh, ''), l.name),
                    'area_km2',
                    ROUND((ST_Area(l.geom::geography) / 1e6)::numeric, 1),
                    'size_category',
                    CASE
                        WHEN ST_Area(l.geom::geography) / 1e6 > 100 THEN '大型'
                        WHEN ST_Area(l.geom::geography) / 1e6 > 10 THEN '中型'
                        ELSE '小型'
                    END
                )
            )
        )
    ) AS geojson
FROM hydrolakes l
    JOIN hydrobasins b ON ST_Contains(b.geom, l.geom) -- 圈流域内的湖
WHERE b.gid = 611;
-- 查询 D：5km 管控区（地图第 4 层 · 绿色大面）
-- 业务：把 M2 那张 24,948 km² 的大绿面画出来 + 附总面积。这是「法规限制开发区」的直观可视化。
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(geom)::jsonb,
                'properties',
                jsonb_build_object(
                    'name',
                    '5km生态管控区',
                    'control_zone_km2',
                    ROUND((ST_Area(geom::geography) / 1e6)::numeric, 2)
                )
            )
        )
    ) AS geojson
FROM demo_control_zone;
-- 查询 E：管控区压到的湖（地图第 5 层 · 高亮叠加）
-- 业务：全图最核心的业务层——绿面压到了哪些湖？压了多少？cover_pct = 被压面积 ÷ 湖总面积，100% 表示湖整体被管控、1% 表示只擦边。
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(
                    (
                        SELECT l.geom
                        FROM hydrolakes l
                        WHERE l.gid = o.gid
                    ) -- 回表取湖几何
                )::jsonb,
                'properties',
                jsonb_build_object(
                    'lake_name',
                    lake_name,
                    'lake_area_km2',
                    lake_area_km2,
                    'overlap_km2',
                    overlap_km2,
                    'cover_pct',
                    ROUND(
                        (overlap_km2 / NULLIF(lake_area_km2, 0) * 100)::numeric,
                        1
                    )
                )
            )
        )
    ) AS geojson
FROM demo_lake_overlay o;
-- 查询 F：湖质心挂名（地图第 6 层 · 文字标签）
-- 业务：地图上要有湖名。取每个湖的中心点放文字标签，避免标签压着湖面。
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(ST_Centroid(l.geom))::jsonb,
                -- 湖中心点
                'properties',
                jsonb_build_object(
                    'gid',
                    l.gid,
                    'lake_name',
                    COALESCE(NULLIF(l.name_zh, ''), l.name)
                )
            )
        )
    ) AS geojson
FROM hydrolakes l
    JOIN hydrobasins b ON ST_Contains(b.geom, l.geom)
WHERE b.gid = 611;
-- 查询 G：统计汇总报表（不进地图 · 给领导做 PPT）
-- 业务：一张纯数字表——几条河、河总长多少、几个湖、管控区多大、河网密度。这是汇报页的「KPI 数字」。
WITH stats AS (
    SELECT (
            SELECT COUNT(*)
            FROM demo_basin_rivers
        ) AS river_count,
        (
            SELECT COALESCE(SUM(ST_Length(geom::geography)) / 1000, 0)
            FROM demo_basin_rivers
        ) AS river_length_km,
        (
            SELECT COUNT(*)
            FROM hydrolakes l
                JOIN hydrobasins b ON ST_Contains(b.geom, l.geom)
            WHERE b.gid = 611
        ) AS lake_count,
        (
            SELECT ST_Area(geom::geography) / 1e6
            FROM demo_control_zone
        ) AS control_zone_km2
)
SELECT river_count,
    ROUND(river_length_km::numeric, 1) AS river_length_km,
    lake_count,
    ROUND(control_zone_km2::numeric, 2) AS control_zone_km2,
    ROUND(
        (river_length_km / NULLIF(control_zone_km2, 0))::numeric,
        2
    ) AS density_km_per_km2
FROM stats;