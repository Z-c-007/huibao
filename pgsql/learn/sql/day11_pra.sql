、 业务背景介绍 -- 水利部"全国河湖管理一张图"入库接口
-- 业务方是水利部信息中心数据汇交组。
-- 各省水利厅每年向部里汇交河湖矢量数据，
-- 但他们传上来的坐标系千奇百怪——有的用 WGS84（GPS 经纬度），
-- 有的用 CGCS2000（中国国标），有的用各省自己定义的高斯投影（3 度带/6 度带），甚至有的带号都不对。
-- 你的任务：后端接收数据包后，
-- 统一转成 CGCS2000 经纬度（4490）入库，
-- 同时转成一套米制投影（4527）存到另一列供量算。
-- 数学上，"同一个点在不同坐标系下是两个不同的坐标值"——如果不做投影转换，
-- 直接拿两个不同 SRID 的几何做 ST_Intersects，PG 会直接报错："Operation on mixed SRID geometries"。
-- 为什么必须在后端做？ 
-- 前端 MapLibre/Cesium 用的 Web Mercator（3857）是纯显示投影，量算面积误差可达 40% 以上。
-- 水利工程决不允许"地图上画的线长 100 米，数据库算出来才 80 米"。
-- 为什么今天必须学？
--  Day 6-9 你一直在用的 geom::geography 本质上是一种"隐式投影转换"（球面 → 球面距离），
-- 但在实际工程中你需要显式 ST_Transform 把数据转到合适投影再做量算。
-- Day 10 刚讲过"列被函数包裹 → 索引作废"，ST_Transform(geom, 3857) 就是典型的函数包裹。
-- 1
-- spatial_ref_sys 是 PostGIS 的内置系统表，存了 5500+ 个 EPSG 坐标系定义
-- srtext 字段是 OGC WKT 格式的完整定义（含椭球体、投影方法、参数）
SELECT srid,
    auth_name,
    auth_srid,
    srtext
FROM spatial_ref_sys
WHERE srid IN (4326, 4490, 3857, 4527);
-- 北京到上海：经度差约 5.1°，纬度差约 8.7°
-- 在 4326（地理坐标系）下直接算 ST_Length，单位是"度"——无物理意义
SELECT ST_Length(
        ST_GeomFromText('LINESTRING(116.4 39.9, 121.5 31.2)', 4326)
    ) AS length_in_degrees,
    -- 返回约 10.1，单位是度，毫无意义
    ST_Length(
        ST_GeomFromText('LINESTRING(116.4 39.9, 121.5 31.2)', 4326)::geography
    ) AS length_in_meters;
-- 把北京的一个点从 4326（WGS84 经纬度）转到 3857（Web Mercator 米制投影）
SELECT ST_AsText(
        ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)
    ) AS wgs84_deg,
    -- POINT(116.4 39.9)
    ST_AsText(
        ST_Transform(
            ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326),
            3857
        )
    ) AS mercator_m;
-- POINT(12957608.2... 4840001.5...)
SELECT DISTINCT ST_SRID(geom)
FROM hydrorivers;
SELECT gid,
    ROUND((ST_Length(geom)::numeric), 2) AS length_deg,
    -- 几何坐标系下算，单位度
    ROUND((ST_Length(geom::geography) / 1000)::numeric, 2) AS length_km_geog,
    -- geography 球面算
    ROUND(
        (ST_Length(ST_Transform(geom, 4527)) / 1000)::numeric,
        2
    ) AS length_km_proj -- 投影平面算
FROM hydrorivers
LIMIT 5;