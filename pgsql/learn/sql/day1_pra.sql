-- 你是给河长制平台做数据核查的。已有三张表：
-- 流域表：河长制的管辖单元
CREATE TABLE basin (
    id SERIAL PRIMARY KEY,
    basin_name VARCHAR(30)
);
-- 水文站点表：每个站属于某个流域
CREATE TABLE station (
    id SERIAL PRIMARY KEY,
    station_name VARCHAR(30),
    basin_id INT,
    -- 指向 basin.id（可能为 NULL = 没登记流域）
    annual_flow NUMERIC
);
-- 河流表：每条河属于某个流域
CREATE TABLE river (
    id SERIAL PRIMARY KEY,
    river_name VARCHAR(30),
    basin_id INT
);
-- 种子里故意埋了三种脏数据 ， 正是为了引出今天所有知识点 ：
INSERT INTO basin (basin_name)
VALUES ('长江流域'),
    ('黄河流域'),
    ('海河流域'),
    ('松花江流域');
-- ④松花江是"空流域"，没站点
INSERT INTO station (station_name, basin_id, annual_flow)
VALUES ('寸滩站', 1, 450.0),
    ('宜昌站', 1, 430.5),
    -- 长江流域 2 个站
    ('兰州站', 2, 310.0),
    ('花园口站', 2, 280.5),
    -- 黄河流域 2 个站
    ('张家口站', 3, 12.5),
    -- 海河流域 1 个站
    ('松花江站', NULL, 90.0),
    -- ⑤孤儿站：basin_id 是 NULL
    ('珠江口站', 99, 800.0);
-- ⑥错挂站：basin_id=99，根本不存在的流域
INSERT INTO river (river_name, basin_id)
VALUES ('长江', 1),
    ('汉江', 1),
    ('黄河', 2),
    ('海河', 3);
-- 长江流域挂 2 条河
SELECT *
FROM river;
SELECT *
FROM station;
SELECT *
FROM basin;
-- 每个站点属于哪个流域？
SELECT s.station_name,
    b.basin_name
FROM station s
    INNER JOIN basin b ON s.basin_id = b.id
ORDER BY s.id;
-- 河长要看到全部站点，即使某个站还没登记流域，也不能漏。
SELECT s.station_name,
    b.basin_name
FROM station s
    LEFT JOIN basin b ON s.basin_id = b.id
ORDER BY s.id;
-- 业务：找出空流域，准备新建水文站。
SELECT b.basin_name
FROM basin b
    LEFT JOIN station s ON s.basin_id = b.id
WHERE s.id IS NULL;
-- 核对"站点表"和"流域表"谁多谁少、谁挂了不存在的流域。
SELECT s.station_name,
    b.basin_name
FROM station s
    FULL JOIN basin b ON s.basin_id = b.id
ORDER BY b.id NULLS LAST,
    s.id;
-- 河长汇报，每个流域要有几个站、几条河。
SELECT b.basin_name,
    COUNT(*) AS join_行数,
    COUNT(DISTINCT s.id) AS 站点数,
    COUNT(DISTINCT r.id) AS 河流数
FROM basin b
    LEFT JOIN station s ON s.basin_id = b.id
    LEFT JOIN river r ON r.basin_id = b.id
GROUP BY b.basin_name
ORDER BY b.basin_name;
-- "全流域核查总览"，但本次只标注长江的站点（其他流域保留，站名留空）
SELECT b.basin_name,
    s.station_name
FROM basin b
    LEFT JOIN station s ON s.basin_id = b.id
    AND b.basin_name = '长江流域'
ORDER BY s.id;
-- 给跨站联动的应急方案用，找出同流域的站点组合
SELECT s1.station_name AS s1,
    s2.station_name AS s2,
    b.basin_name
FROM station s1
    JOIN station s2 ON s1.basin_id = s2.basin_id
    AND s1.id < s2.id
    JOIN basin b ON b.id = s1.basin_id;
SELECT s.station_name,
    b.basin_name
FROM station s
    INNER JOIN basin b USING(id);