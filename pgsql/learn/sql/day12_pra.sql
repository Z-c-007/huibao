-- ============================================================
-- Day 12：投影实战 —— 坐标系决定单位，单位决定量算对不对
-- 库：day3_pra ｜ 表：hydrorivers / hydrobasins / hydrolakes（SRID=4326）
-- 官方依据：PostGIS Workshop §16-17；PostGIS 手册 ST_Transform / ST_Buffer / ST_Area / ST_Length / ST_SRID / ST_SetSRID
-- ============================================================

-- ------------------------------------------------------------
-- 一、业务背景
-- 业务方：长江水利委员会河道管理保护处。
-- 他们要划定每一条河流的"5km 生态缓冲带"，并上报缓冲带面积（km²）。
-- 数据是 WGS84(4326) 经纬度入库的——但 4326 是"度"不是"米"，
-- 直接 ST_Area / ST_Buffer 会得到"平方度 / 度"这种无物理意义的数字。
-- 本日任务：面积与缓冲带必须在米制口径下算（geography 球面 或 4527 投影平面），
--           再转回 4326 输出给前端。
-- ------------------------------------------------------------

-- ============================================================
-- 练习 1：先确认数据真实 SRID（不许默认，先看）
-- ============================================================
-- ST_SRID(geom)：括号里是函数的实参 = 表的空间列名 geom，
-- 返回每个几何的 SRID 标签（int）。全表共享 4326。
SELECT DISTINCT ST_SRID(geom)
FROM hydrorivers;

SELECT DISTINCT ST_SRID(geom)
FROM hydrobasins;
-- 预期：两行都是 4326

-- 【补充】想合并成一张带表名标签的表：UNION ALL 纵向拼接 + 子查询当临时表
-- DISTINCT 必须紧跟 SELECT，不能放在逗号列清单中间（我最初写错过，见沉淀 Q1）
SELECT 'hydrorivers' AS tbl,
    srid
FROM (
        SELECT DISTINCT ST_SRID(geom) AS srid
        FROM hydrorivers
    ) t
UNION ALL
SELECT 'hydrobasins',
    srid
FROM (
        SELECT DISTINCT ST_SRID(geom) AS srid
        FROM hydrobasins
    ) t;
-- 预期：
-- | tbl          | srid |
-- |--------------|------|
-- | hydrorivers  | 4326 |
-- | hydrobasins  | 4326 |

-- ============================================================
-- 练习 2：面积三法对比（同一流域）
-- ============================================================
-- 4527 = EPSG 编码：CGCS2000 / 3-degree Gauss-Kruger zone 39
--       （CGCS2000 基准 + 3 度带高斯投影 + 第 39 带，中央经线 117°E，单位米）
SELECT b.gid,
    b.hybas_id,
    -- 4326 下：单位"平方度"，无物理意义
    ROUND(ST_Area(b.geom)::NUMERIC, 6) AS area_deg2,
    -- geography 球面真实 km²（全球/大尺度推荐）
    ROUND((ST_Area(b.geom::geography) / 1e6)::numeric, 2) AS area_km2_geog,
    -- CGCS2000 高斯投影平面 km²（局域工程推荐）
    ROUND(
        (ST_Area(ST_Transform(b.geom, 4527)) / 1e6)::numeric,
        2
    ) AS area_km2_proj
FROM hydrobasins AS b
WHERE b.gid = 716;  -- 716 为真库已实测可用的 gid；路线 Day 8-10 用的 746 亦可替换
-- 预期：area_deg2 是"平方度"量级（无意义）；后两列应接近（局域球面≈平面，差值<1%）

-- ============================================================
-- 练习 3：两种米制口径的差异百分比（验证哪种更稳）
-- ============================================================
SELECT b.gid,
    ROUND((ST_Area(b.geom::geography) / 1e6)::numeric, 2) AS area_km2_geog,
    ROUND(
        (ST_Area(ST_Transform(b.geom, 4527)) / 1e6)::numeric,
        2
    ) AS area_km2_proj,
    -- 差异百分比 = (geography - 投影) / geography
    ROUND(
        (
            100.0 * (
                ST_Area(b.geom::geography) - ST_Area(ST_Transform(b.geom, 4527))
            ) / ST_Area(b.geom::geography)
        )::numeric,
        3
    ) AS diff_pct
FROM hydrobasins b
WHERE b.gid = 716;
-- 预期：局域尺度 diff_pct 极小（<1%）；若跨省/大尺度差异会变大，那种场景直接用 geography

-- ============================================================
-- 练习 4：生产做法——预计算投影列 + GiST 索引（接 Day 10"函数包裹列→索引作废"）
-- ============================================================
-- CTAS（CREATE TABLE ... AS）：让一条 SELECT 的结果直接落地成一张新表，
-- 相当于"建表 + INSERT"两步的合体，列名/类型自动照搬 SELECT 结果。
-- 这里把 4527 投影结果物化成表，让 geom 成为"裸列"，才能建 GiST 索引。
CREATE TABLE hydrorivers_4527 AS
SELECT gid,
    hyriv_id,
    main_riv,
    ST_Transform(geom, 4527) AS geom  -- 表达式列必须 AS 起名，否则列名叫 st_transform
FROM hydrorivers;

-- GiST 空间索引：拿现有 geom 列另建一份"外接矩形(bbox)"查找结构，
-- 查询时先粗筛矩形再精算。索引不新增列、不改表结构，只加速查询。
CREATE INDEX hydrorivers_4527_geom_idx ON hydrorivers_4527 USING GIST (geom);

-- 验证：投影列 SRID 应是 4527
SELECT DISTINCT ST_SRID(geom)
FROM hydrorivers_4527;

-- ============================================================
-- 练习 5：正确 Buffer——两条米制路
-- ============================================================
-- 4326 下直接 ST_Buffer(geom, 0.05) 是静默错误（半径是"度"不是"米"），见下方陷阱 1。

-- 路线 A：geography（推荐，一句话米制，球面）
SELECT gid,
    ST_AsText(ST_Buffer(geom::geography, 5000)) AS buffer_geom
FROM hydrorivers
WHERE gid = 100;

-- 路线 B：转 4527 平面做 buffer，再转回 4326 输出
SELECT gid,
    ST_AsText(
        ST_Transform(
            ST_Buffer(ST_Transform(geom, 4527), 5000),
            -- 米制投影下做 5km
            4326 -- 转回 WGS84 给前端
        )
    ) AS buffer_geom
FROM hydrorivers
WHERE gid = 100;

-- ============================================================
-- 练习 6：综合——每条河 5km 缓冲带面积（本日业务交付）
-- 嵌套函数从内到外执行：ST_Buffer 先算（扩 5km）→ ST_Area 求面积(m²)
--                         → /1e6 转 km² → ROUND((...)::numeric, 2) 修精度
-- ============================================================
SELECT r.gid,
    r.main_riv,
    ROUND(
        (ST_Length(r.geom::geography) / 1000)::numeric,
        1
    ) AS length_km,
    ROUND(
        (
            ST_Area(ST_Buffer(r.geom::geography, 5000)) / 1e6
        )::numeric,
        2
    ) AS area_km2
FROM hydrorivers r
ORDER BY length_km DESC
LIMIT 10;
-- 预期：按河长倒序，输出每条河的 5km 缓冲带面积 km²

-- ============================================================
-- 生产版：真实环境怎么写（练习版 vs 生产版）
-- 生产不会对 143 万行逐行现算 geography buffer（太慢），而是分步物化+复用
-- ============================================================

-- 生产 ①：后台定时任务，一次性物化所有河的 5km 缓冲带（只算一次）
CREATE TABLE river_buffer_5km AS
SELECT gid,
    hyriv_id,
    main_riv,
    ST_Buffer(geom::geography, 5000)::geometry AS geom -- 转回 geometry 存，好建索引
FROM hydrorivers;

CREATE INDEX river_buffer_5km_geom_idx ON river_buffer_5km USING GIST (geom);

-- 工程规范：写注释，不然三个月后没人记得这张表是啥
COMMENT ON TABLE river_buffer_5km IS '河流5km生态缓冲带（geography米制缓冲后转4326存geometry）';

-- 生产 ②：接口层只 SELECT，不现算
SELECT gid,
    main_riv,
    ROUND((ST_Length(geom::geography) / 1000)::numeric, 1) AS len_km,
    ROUND((ST_Area(geom::geography) / 1e6)::numeric, 2) AS buf_area_km2
FROM river_buffer_5km
ORDER BY buf_area_km2 DESC
LIMIT 10;

-- 生产 ③：按流域统计缓冲带覆盖面积——先 ST_Intersection 裁剪再求和，
--        防"穿多流域的整条河被重复计数"（模板强制项 #4）
SELECT b.gid AS basin_gid,
    COUNT(DISTINCT rb.gid) AS river_cnt,
    ROUND(
        (
            SUM(ST_Area(ST_Intersection(rb.geom, b.geom)::geography)) / 1e6
        )::numeric,
        2
    ) AS buf_area_in_basin_km2
FROM hydrobasins b
    LEFT JOIN river_buffer_5km rb ON ST_Intersects(rb.geom, b.geom)
GROUP BY b.gid
ORDER BY buf_area_in_basin_km2 DESC
LIMIT 10;

-- 生产 ④：给前端输出 GeoJSON（4326 输出，前端直接渲染；接 Day 16 mini 项目）
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(geom)::jsonb, -- 4326 输出，前端能直接画
                'properties',
                jsonb_build_object('gid', gid, 'main_riv', main_riv)
            )
        )
    ) AS geojson
FROM river_buffer_5km
WHERE gid = 100;

-- ============================================================
-- 五、错误与陷阱（故意跑错，看后果）
-- ============================================================

-- 陷阱 1：4326 下直接 ST_Buffer → 静默错误（最危险，能跑通但结果错）
-- 你以为 0.05 ≈ 5km？1°≈111km，0.05°≈5.6km，且随纬度变化——半径是"度"，不是"米"
SELECT ST_AsText(
        ST_Buffer(ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326), 0.05)
    ) AS bad_buffer;
-- 正确写法（二选一）：
SELECT ST_AsText(
        ST_Buffer(ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)::geography, 5000)
    ) AS good_buffer;

-- 陷阱 2：ST_Transform 输入 SRID=0 → 直接报错
SELECT ST_Transform('POINT(116.4 39.9)'::geometry, 4527);
-- 报错：ERROR: Input geometry has unknown(0) SRID
-- 修正：先 ST_SetSRID('...'::geometry, 4326) 再 ST_Transform

-- 陷阱 3：ROUND(double, n) 报错（模板强制项 #1）
SELECT ROUND(ST_Area(geom), 2)
FROM hydrobasins
LIMIT 1;
-- 报错：function round(double precision, integer) does not exist
-- 修正：ROUND((表达式)::numeric, n)

-- ============================================================
-- 自检题（口头能答出 = 过关，详见沉淀 Day12 文档）
-- 独立练习：见沉淀 Day12 文档第九节
-- ============================================================
