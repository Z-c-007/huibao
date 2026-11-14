-- w8_10_schema.sql ｜ ai_water_budget 建模 + GiST 索引（幂等：DROP IF EXISTS 前置，可重复执行）
-- 设计决策：
--   1. 存储 SRID=4326（经纬度，与源数据/前端 Cesium 一致）；量算用 ::geography 转换（Day 11 SQL 体现）
--   2. water_users 不设 street_id 外键——街道/区县归属由查询时 ST_Within 空间 JOIN 推导（体现 PostGIS 价值）
--   3. rivers.geometry 用 MultiLineString 承接 HydroRIVERS 源数据类型
--   4. 每张空间表建 GiST 索引（等价 shp2pgsql -I）
\encoding UTF8
\c ai_water_budget

DROP TABLE IF EXISTS water_users CASCADE;
DROP TABLE IF EXISTS rivers CASCADE;
DROP TABLE IF EXISTS streets CASCADE;
DROP TABLE IF EXISTS districts CASCADE;

CREATE TABLE districts (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    geom geometry(Polygon, 4326) NOT NULL
);

CREATE TABLE streets (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    district_id INTEGER NOT NULL REFERENCES districts (id),
    geom        geometry(Polygon, 4326) NOT NULL,
    UNIQUE (district_id, name)
);

CREATE TABLE rivers (
    id       SERIAL PRIMARY KEY,
    hyriv_id BIGINT UNIQUE,                      -- HydroRIVERS 河段 ID（保留溯源能力）
    name     TEXT NOT NULL DEFAULT '潮白河',
    ord_stra SMALLINT,                           -- Strahler 阶数（便于后续按干流/支流过滤）
    geom     geometry(MultiLineString, 4326) NOT NULL
);

CREATE TABLE water_users (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    industry   TEXT NOT NULL,                    -- 白名单见 backend validator：制造业/服务业/农业/建筑业
    water_used NUMERIC NOT NULL,
    budget     NUMERIC NOT NULL,
    geom       geometry(Point, 4326) NOT NULL
);

CREATE INDEX districts_geom_gix   ON districts   USING GIST (geom);
CREATE INDEX streets_geom_gix     ON streets     USING GIST (geom);
CREATE INDEX rivers_geom_gix      ON rivers      USING GIST (geom);
CREATE INDEX water_users_geom_gix ON water_users USING GIST (geom);
