-- ============================================
-- Day 3：空间数据加载与验证（PostGIS Workshop §4-5）
-- 库：day3_pra  |  PG 18.4  |  PostGIS 3.6.2
-- ============================================
-- ⚠️ 本机数据与学习路线不一致的三处（后续 Day 4-15 必须按实际字段写）：
--   1. hydrorivers 字段是 main_riv（不是 main_river）—— DBF 10 字符截断
--   2. hydrolakes 是 Natural Earth（ne_10m），没有 hylak_id/lake_name，
--      用 name / name_zh（含中文名）
--   3. hydrobasins.hybas_id 是 double precision（浮点），不是整型
-- ============================================

-- ============================================
-- 0. 数据是怎么进来的（shell 命令，非 SQL，但要懂参数）
-- ============================================
-- shp2pgsql -I -s 4326 HydroRIVERS_v10_as.shp public.hydrorivers | psql -d day3_pra
--   -I   自动创建 GiST 空间索引
--   -s 4326  声明坐标系为 WGS84 经纬度
--   public.hydrorivers  = schema.表名
--   | psql  管道直接把生成 SQL 喂给 psql

-- ============================================
-- 1. 验证行数（Day 3 自检判定标准）
-- ============================================
SELECT COUNT(*)
FROM hydrorivers;    -- 1,428,959
SELECT COUNT(*)
FROM hydrobasins;    -- 2,489
SELECT COUNT(*)
FROM hydrolakes;     -- 1,355

-- ============================================
-- 2. 看数据长什么样（认识字段）
-- ============================================
SELECT *
FROM hydrorivers
LIMIT 3;
SELECT *
FROM hydrobasins
LIMIT 3;
SELECT *
FROM hydrolakes
LIMIT 3;

-- ============================================
-- 3. 查空间元数据（Day 3 核心）
--    geometry_columns 是 PostGIS 安装时建的"标准目录视图"，
--    7 列是 SQL/MM 标准契约，换任何数据源列名都不变、只有行实时变。
--    \dv           看库里有哪几个视图
--    \d geometry_columns   看视图有哪些列
-- ============================================
SELECT f_table_name,
    f_table_schema,
    f_table_catalog,
    coord_dimension,
    f_geometry_column,
    srid,
    type
FROM geometry_columns
WHERE f_table_name IN ('hydrorivers', 'hydrobasins', 'hydrolakes');
-- 期望：三张表都可见，geom 列，srid=4326，
--        hydrorivers=MultiLineString，hydrobasins/hydrolakes=MultiPolygon

-- ============================================
-- 4. 检查空间索引（验证 shp2pgsql -I 生效）
-- ============================================
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('hydrorivers', 'hydrobasins', 'hydrolakes')
ORDER BY tablename;
-- 期望：三表各有 gist (geom) —— 没有的话大表空间查询会很慢（Day 10 会讲）

-- ============================================
-- 5. SRID 补救命令（本机 srid 已是 4326，无需执行，仅备防）
--    什么时候用：导入后 geometry_columns 显示 srid=0
--    （shp 缺 .prj 或 shp2pgsql 漏了 -s）
-- ============================================
-- ALTER TABLE hydrorivers
-- ALTER COLUMN geom TYPE geometry(MultiLineString, 4326)
-- USING ST_SetSRID(geom, 4326);

-- ============================================
-- 6. Day 3 自检
-- ============================================
--  ① 三张表在 geometry_columns 中可见？各是什么几何类型、什么 SRID？
--  ② SELECT COUNT(*) 返回合理数值（河流百万级、流域/湖泊千级）？
--  ③ hydrorivers 里"干流名"字段实际叫什么？（答：main_riv，不是 main_river）
