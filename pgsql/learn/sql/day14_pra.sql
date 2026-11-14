-- ============================================================
-- Day 14：几何构造函数 —— 缓冲 / 并 / 交 / 差 / 质心 / 凸包
-- 库：day3_pra ｜ 表：hydrorivers / hydrobasins / hydrolakes（SRID=4326）
--       + 本日新建：test_overlap（演示表）/ stations（水文站，接 Day 13）
-- 官方依据：PostGIS Workshop §20-21；PostGIS 手册
--   ST_Buffer / ST_Union / ST_Intersection / ST_Difference / ST_Centroid
--   / ST_ConvexHull / ST_Collect / ST_MakeEnvelope / ST_PointOnSurface
-- ============================================================

-- ------------------------------------------------------------
-- 一、业务背景
-- 业务方：市水务局河湖管理处 + 防汛办，"河湖管理范围划定与生态空间管控一张图"。
-- 需求：
--   ① 河长制考核：给重点河流划 5km 生态缓冲带，上报"连续管控区总面积"（多河重叠要合并去重）；
--   ② 管控区覆盖了哪些流域、重叠多大（ST_Intersection）；
--   ③ 管控区减去城镇建成区，剩多少"可调整生态空间"（ST_Difference）；
--   ④ 每个湖的质心，用于地图挂名挂牌（ST_Centroid）；
--   ⑤ 一组水文站的外包络，快速看"监测覆盖范围"（ST_ConvexHull）。
-- 为什么必须今天学：Day 12 只会"一条河一个缓冲带"（ST_Buffer 单对象）；
--   今天学的 Union/Intersection/Difference/Centroid/ConvexHull 是把多个几何
--   "拼、裁、减、取心、取壳"的工具——空间分析从"单对象"迈向"多对象集合操作"的分水岭。
-- 核心分工（本日最重要）：集合运算（Union/Intersection/Difference）只有 geometry 版；
--   量算（面积/长度）再 ::geography。"集合运算用 geometry，量算再 ::geography"。
-- ------------------------------------------------------------

-- ============================================================
-- 练习 0：建演示表 test_overlap（集合运算四件套的"试验田"）
-- ============================================================
-- 两个重叠的正方形：A=(0,0)-(5,5)，B=(3,3)-(8,8)，重叠区 = 正方形(3,3)-(5,5)
-- DROP + CREATE：可重复执行，重复跑 INSERT 不会攒出重复行
DROP TABLE IF EXISTS test_overlap;
CREATE TABLE test_overlap (id INT, geom geometry);
INSERT INTO test_overlap VALUES
    (1, 'POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))'),
    (2, 'POLYGON((3 3, 8 3, 8 8, 3 8, 3 3))');

-- ============================================================
-- 练习 1：ST_Buffer —— 河流 5km 生态缓冲带（Day 12 复习 + 本日主角）
-- ============================================================
-- 嵌套从内到外：ST_Buffer（扩 5km 造面）→ ST_Area（量面积 m²）→ /1e6（转 km²）→ ROUND
-- geom::geography 转球面 → ST_Buffer 单位才是米（强制项 #3，禁止在 4326 直接 buffer）
SELECT gid,
    ROUND((ST_Length(geom::geography) / 1000)::numeric, 1)                AS length_km,
    ROUND((ST_Area(ST_Buffer(geom::geography, 5000)) / 1e6)::numeric, 2) AS buffer_area_km2
FROM hydrorivers
WHERE gid = 100;
-- 预期：| gid | length_km | buffer_area_km2 |（河长 km / 缓冲带面积 km²）

-- ============================================================
-- 练习 2：ST_Union —— 把多条河的缓冲带合并成"一张连续管控区"
-- ============================================================
-- 业务：多条河缓冲带相互重叠，上报面积要"合并去重后的一张连续面"。
-- 三步 cast 各有理由：
--   ① sr.geom::geography         → 缓冲半径 5000 才是"米"
--   ② ST_Buffer(...)::geometry   → ST_Union 只有 geometry 版（geography 没有 Union 函数！）
--   ③ ST_Union(...)::geography   → 合并结果量米制面积要走球面
-- ST_Union(geom) 是聚合函数：把多行几何焊成一个、重叠自动消掉。
-- 注意：DISTINCT ON 不写 ORDER BY 时"每组取哪一行"不确定（生产必须补 ORDER BY，见下方生产版）
WITH sel_rivers AS (
    SELECT DISTINCT ON (r.main_riv) r.gid, r.main_riv, r.geom
    FROM hydrorivers r
    JOIN hydrobasins b ON ST_Intersects(b.geom, r.geom)   -- 显式 JOIN（强制项 #6）
    WHERE b.gid = 716
)
SELECT ROUND((ST_Area(
    ST_Union(ST_Buffer(sr.geom::geography, 5000)::geometry)::geography
) / 1e6)::numeric, 2) AS merged_control_zone_km2
FROM sel_rivers sr;
-- 预期：合并后的连续管控区面积 km²，< 各条河缓冲带面积之和（重叠被消掉）

-- 演示表直观版：Union（聚合）vs 二元
SELECT ST_AsText(ST_Union(geom)) AS merged
FROM test_overlap;
-- 预期：POLYGON((0 0,5 0,5 3,8 3,8 8,3 8,3 5,0 5,0 0))（阶梯形，重叠溶解，顶点顺序可能微调）

SELECT ST_AsText(ST_Union(
    'POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))'::geometry,
    'POLYGON((3 3, 8 3, 8 8, 3 8, 3 3))'::geometry
)) AS merged_binary;

-- 练习 2-生产版：DISTINCT ON 加 ORDER BY，取每个干流最长的一段当代表（确定性）
-- WITH sel_rivers AS (
--     SELECT DISTINCT ON (r.main_riv) r.gid, r.main_riv, r.geom
--     FROM hydrorivers r
--     JOIN hydrobasins b ON ST_Intersects(b.geom, r.geom)
--     WHERE b.gid = 716
--     ORDER BY r.main_riv, ST_Length(r.geom::geography) DESC
-- )
-- SELECT ...（同上）...

-- ============================================================
-- 练习 3：ST_Intersection —— 管控区与流域的重叠面积
-- ============================================================
-- 业务：管控区（三条河缓冲带合并）横跨多个流域，要"切开、各自只量自己那份"。
-- 先按 Day 12 生产口径：geometry 求交，再把交结果 ::geography 量米制面积。
-- ST_Intersects 是"有没有交"（布尔，当 JOIN 条件）；ST_Intersection 是"交多大"（几何，切出来量面积）。
-- 注意：真库可能返回 0 行——三条河 5km 缓冲带相对亚洲流域尺度很小，不一定和 gid=746 相交！
--   0 行 = 空间上确实没交（正常现象，不是 bug）；想看到值就跑下方"诊断版"换一个流域。
WITH control_zone AS (
    SELECT ST_Union(ST_Buffer(r.geom::geography, 5000)::geometry) AS geom
    FROM hydrorivers r
    WHERE r.gid IN (100, 101, 102)
)
SELECT ROUND((ST_Area(
    ST_Intersection(cz.geom, b.geom)::geography
) / 1e6)::numeric, 2) AS overlap_km2
FROM control_zone cz
JOIN hydrobasins b ON ST_Intersects(cz.geom, b.geom)
WHERE b.gid = 746;
-- 预期：| overlap_km2 |（管控区落在流域 746 内的那部分面积 km²；若 0 行说明没交，跑诊断版）

-- 诊断版：不看特定流域，看管控区到底和哪些流域相交（各切各的、面积分摊口径）
-- WITH control_zone AS (
--     SELECT ST_Union(ST_Buffer(r.geom::geography, 5000)::geometry) AS geom
--     FROM hydrorivers r
--     WHERE r.gid IN (100, 101, 102)
-- )
-- SELECT b.gid,
--     ROUND((ST_Area(ST_Intersection(cz.geom, b.geom)::geography) / 1e6)::numeric, 2) AS overlap_km2
-- FROM control_zone cz
--     JOIN hydrobasins b ON ST_Intersects(cz.geom, b.geom)
-- ORDER BY overlap_km2 DESC;
-- 再把返回里的实际 b.gid 替换掉 746 即可

-- 演示表直观版：交集 = 两个正方形的公共小块
SELECT ST_AsText(ST_Intersection(
    'POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))'::geometry,
    'POLYGON((3 3, 8 3, 8 8, 3 8, 3 3))'::geometry
)) AS intersection;
-- 预期：POLYGON((3 3, 5 3, 5 5, 3 5, 3 3))

-- ============================================================
-- 练习 4：ST_Difference —— 管控区减去"城镇已建成区"，得可调整生态空间
-- ============================================================
-- ST_Difference(A, B)：A 中与 B 不相交的部分（A - Intersection(A,B)）。
-- 官方：这是唯一"输入顺序有意义"的 overlay 函数，结果永远是 A 的一部分。
-- ST_MakeEnvelope(左下x, 左下y, 右上x, 右上y, srid)：造矩形（代表建成区保留范围）
--   注意：第 5 个参数 srid 必写，否则得到 SRID=0 的矩形，和 4326 求交会报 mixed SRID
WITH control_zone AS (
    SELECT ST_Union(ST_Buffer(r.geom::geography, 5000)::geometry) AS geom
    FROM hydrorivers r
    WHERE r.gid IN (100, 101, 102)
)
SELECT ROUND((ST_Area(
    ST_Difference(cz.geom,
        ST_MakeEnvelope(115.9, 39.7, 116.1, 39.9, 4326)
    )::geography
) / 1e6)::numeric, 2) AS adjustable_zone_km2
FROM control_zone cz;
-- 预期：| adjustable_zone_km2 |（管控区扣掉矩形后的可调整面积 km²）

-- 演示表直观版：A 减 B（L 形）
SELECT ST_AsText(ST_Difference(
    'POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))'::geometry,   -- A
    'POLYGON((3 3, 8 3, 8 8, 3 8, 3 3))'::geometry    -- B
)) AS difference;
-- 预期：POLYGON((0 0, 5 0, 5 3, 3 3, 3 5, 0 5, 0 0))（L 形）

-- ============================================================
-- 练习 5：ST_Centroid —— 湖泊质心（地图挂名/挂牌点）
-- ============================================================
-- 面积最大的 5 个湖，取质心点坐标用于前端标注。
-- 注意：质心是面积加权重心，凹多边形/带洞时可能落在面外；要"一定在面内"用 ST_PointOnSurface
SELECT gid,
    name_zh,
    ST_AsText(ST_Centroid(geom)) AS centroid_wkt,
    ROUND((ST_Area(geom::geography) / 1e6)::numeric, 2) AS area_km2
FROM hydrolakes
ORDER BY ST_Area(geom::geography) DESC
LIMIT 5;
-- 预期：| gid | name_zh | centroid_wkt | area_km2 |（最大湖在前，质心 POINT(经 纬)）

-- 演示版：正方形质心应在正中心
SELECT ST_AsText(ST_Centroid('POLYGON((0 0, 5 0, 5 5, 0 5, 0 0))'::geometry));
-- 预期：POINT(2.5 2.5)

-- ============================================================
-- 练习 6：ST_ConvexHull —— 水文站群外包络（监测覆盖范围）
-- ============================================================
-- 建站表（幂等，可重复执行；同 Day 13 的 stations）
DROP TABLE IF EXISTS stations;
CREATE TABLE stations (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(20),
    geom geometry(Point, 4326)
);
INSERT INTO stations (name, geom) VALUES
    ('北京站',     ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)),
    ('上海站',     ST_SetSRID(ST_MakePoint(121.5, 31.2), 4326)),
    ('武汉站',     ST_SetSRID(ST_MakePoint(114.3, 30.6), 4326)),
    ('广州站',     ST_SetSRID(ST_MakePoint(113.3, 23.1), 4326)),
    ('乌鲁木齐站', ST_SetSRID(ST_MakePoint(87.6, 43.8), 4326));

-- ST_ConvexHull 不是聚合函数、只收一个几何 → 必须先 ST_Collect 把 5 行的点攒成一个 MULTIPOINT
-- ST_Collect = "装盒"（几何原封不动）；ST_ConvexHull = "绷皮筋"（最小凸多边形）
SELECT ST_AsText(ST_ConvexHull(ST_Collect(geom))) AS hull_wkt
FROM stations;
-- 预期：覆盖北京→广州→乌鲁木齐的凸多边形（顶点是最外圈几个站，中间站被包住）

-- 演示：ST_Collect 只装不合并（和 Union 的区别）
SELECT ST_AsText(ST_Collect(geom)) AS collected
FROM test_overlap;
-- 预期：两个不消重叠的正方形被装进一个容器（不是 Union 的阶梯形）

-- ============================================================
-- 练习 7：综合交付 —— 给前端的 GeoJSON（接 Day 16）
-- ============================================================
-- 管控区以 4326 GeoJSON 输出给前端（前端 MapLibre 要经纬度）。
-- jsonb_build_object 拼"对象"；jsonb_agg 收"数组"；ST_AsGeoJSON 几何→GeoJSON 文本；
-- ::jsonb 把文本解析成"真正的嵌套 JSON"（不转 → 值变成带引号的转义字符串）；
-- AS geojson 只是列别名，不是导出文件（导出文件是 psql \copy 的活，Day 16）
WITH control_zone AS (
    SELECT ST_Union(ST_Buffer(r.geom::geography, 5000)::geometry) AS geom
    FROM hydrorivers r
    WHERE r.gid IN (100, 101, 102)
)
SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(geom)::jsonb,
                'properties', jsonb_build_object('name', '河湖生态管控区')
            )
        )
    ) AS geojson
FROM control_zone;
-- 预期：一条 FeatureCollection，geometry 是 4326，前端直接能画

-- ============================================================
-- 错误与陷阱（故意跑错，看后果）
-- ============================================================

-- 陷阱 1：对 geography 直接 ST_Union —— 报错
SELECT ST_Union(ST_Buffer(geom::geography, 5000))
FROM hydrorivers WHERE gid = 100;
-- 报错：函数 st_union(geography) 不存在（集合运算只有 geometry 版）
-- 修正：ST_Union(ST_Buffer(geom::geography, 5000)::geometry)

-- 陷阱 2：4326 下直接 ST_Buffer(geom, 5000) —— 静默错误
-- 5000 是"度"不是"米"（1°≈111km），半径变 55 万 km，面积天文数字、不报错
SELECT ROUND((ST_Area(ST_Buffer(geom, 5000)))::numeric, 2)
FROM hydrorivers WHERE gid = 100;
-- 修正：ST_Buffer(geom::geography, 5000)

-- 陷阱 3：ST_Intersection / ST_Difference 两侧 SRID 不一致 —— 报错
-- ST_MakeEnvelope 漏第 5 个参数 srid → 得到 SRID=0 的矩形
SELECT ST_Intersection(
    geom,
    ST_MakeEnvelope(115.9, 39.7, 116.1, 39.9)   -- 缺 4326
)
FROM hydrorivers WHERE gid = 100;
-- 报错：Operation on mixed SRID geometries (Polygon, 4326) != (Polygon, 0)
-- 修正：ST_MakeEnvelope(..., 4326)

-- 陷阱 4：ST_Centroid 可能落在多边形外面 —— 静默错误
-- 带洞（环形）多边形：质心可能落在洞里/面外，挂名挂到河对岸
SELECT ST_AsText(ST_Centroid(
    'POLYGON((0 0, 10 0, 10 10, 0 10, 0 0), (2 2, 2 8, 8 8, 8 2, 2 2))'
));
-- 修正：要"一定在面内"的标注点用 ST_PointOnSurface(geom)

-- 陷阱 5：ROUND(double, n) 报错（强制项 #1，贯穿全链）
SELECT ROUND(ST_Area(ST_Union(geom)), 2) FROM test_overlap;
-- 报错：function round(double precision, integer) does not exist
-- 修正：ROUND((ST_Area(...))::numeric, 2)

-- ============================================================
-- 自检题（口头能答出 = 过关，详见沉淀 Day14 文档）
-- 独立练习：见沉淀 Day14 文档第九节
-- ============================================================
