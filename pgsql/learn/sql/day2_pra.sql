-- 可安全重跑：先清掉旧表，避免 "relation already exists"
DROP TABLE IF EXISTS station, basin, river;

CREATE TABLE station (
    id SERIAL PRIMARY KEY,
    station_name VARCHAR(30),
    basin VARCHAR(30),
    river VARCHAR(30),
    annual_flow NUMERIC
);
CREATE TABLE basin (id SERIAL PRIMARY KEY, basin_name VARCHAR(30));
CREATE TABLE river (
    id SERIAL PRIMARY KEY,
    river_name VARCHAR(30),
    basin_name VARCHAR(30)
);
-- 种子：2 个站点缺测流量(annual_flow=NULL)、1 个站点河流未登记(river=NULL)、1 个空流域
INSERT INTO station (station_name, basin, river, annual_flow)
VALUES ('张家口水文站', '海河流域', '洋河', 12.5),
    ('官厅水文站', '海河流域', '永定河', 45.2),
    ('密云水文站', '海河流域', '潮白河', NULL),
    -- 缺测
    ('宜昌水文站', '长江流域', '长江', 450.0),
    ('汉口水文站', '长江流域', '长江', 380.5),
    ('大通水文站', '长江流域', '长江', 300.0),
    ('寸滩水文站', '长江流域', '嘉陵江', NULL),
    -- 缺测
    ('兰州水文站', '黄河流域', '黄河', 310.0),
    ('花园口水文站', '黄河流域', '黄河', 280.5),
    ('陇西雨量站', '黄河流域', NULL, 5.8);
-- 河流未登记
INSERT INTO basin (basin_name)
VALUES ('海河流域'),
    ('长江流域'),
    ('黄河流域'),
    ('淮河流域');
-- 淮河 = 空流域，无站
INSERT INTO river (river_name, basin_name)
VALUES ('长江', '长江流域'),
    ('汉江', '长江流域'),
    ('嘉陵江', '长江流域'),
    ('黄河', '黄河流域'),
    ('洋河', '海河流域'),
    ('永定河', '海河流域');
-- 注意：密云的'潮白河'在 river 表里没有登记 → 故意埋的
SELECT *
FROM station;
SELECT *
FROM basin;
SELECT *
FROM river;

-- ============================================
-- 实验 A：去掉 COALESCE，看淮河那行的 NULL（体会为什么要补 0）
-- ============================================
SELECT b.basin_name, s.站数, s.总流量
FROM basin b
LEFT JOIN (
    SELECT basin, COUNT(*) AS 站数, SUM(annual_flow) AS 总流量 FROM station GROUP BY basin
) s ON s.basin = b.basin_name;

-- ============================================
-- 实验 B：COUNT(*) 对空分组无行 → NULL 的根源
-- ============================================
SELECT basin, COUNT(*) FROM station WHERE basin = '淮河流域' GROUP BY basin;
-- 期望：0 行结果（没有淮河的行 → LEFT JOIN 后淮河一侧全 NULL）

-- ============================================
-- 实验 C：NULL 传染现象旁证
-- ============================================
SELECT NULL + 100 AS 结果;   -- NULL

-- ============================================
-- 实验 D：AVG/ROUND 参数验证（`1` 是 ROUND 的，不是 AVG 的）
-- ============================================
SELECT basin,
       AVG(annual_flow)           AS 精确平均,     -- 长江 376.8333...
       ROUND(AVG(annual_flow), 1) AS 保留1位,      -- 376.8
       ROUND(AVG(annual_flow), 0) AS 保留0位,      -- 377
       SUM(annual_flow) / COUNT(annual_flow) AS 平均手动
FROM station
GROUP BY basin;
-- 全表聚合 → COUNT 三兄弟 + NULL 被忽略
SELECT COUNT(*) AS 总行数,
    COUNT(annual_flow) AS 有流量行数,
    COUNT(*) - COUNT(annual_flow) AS 无流量行数,
    COUNT(DISTINCT basin) AS 流域数,
    COUNT(DISTINCT river) AS 河流数,
    SUM(annual_flow) AS 总流量,
    ROUND(AVG(annual_flow), 1) AS 平均流量,
    MAX(annual_flow) AS 最大流量
FROM station;
-- GROUP BY 单列 —— 每流域统计
SELECT basin,
    COUNT(*) AS 站数,
    ROUND(SUM(annual_flow), 1) AS 总流量,
    ROUND(AVG(annual_flow), 1) AS 平均流量
FROM station
GROUP BY basin;
-- 多列 GROUP BY + NULL 自成一组
SELECT basin,
    river,
    COUNT(*) AS 站数
FROM station
GROUP BY basin,
    river;
-- 需求：总流量 ≥ 300 的流域
SELECT basin,
    ROUND(SUM(annual_flow), 1) AS total
FROM station
GROUP BY basin
HAVING SUM(annual_flow) >= 300;
-- ① 分组前过滤行：只要"流量≥100 且 河流已登记"的站点，再按流域统计
SELECT basin,
    COUNT(*) AS 站数,
    ROUND(SUM(annual_flow), 1) AS 总流量,
    ROUND(AVG(annual_flow), 1) AS 平均流量
FROM station
WHERE annual_flow >= 100
    AND river IS NOT NULL
GROUP BY basin;
-- ② 故意跑错：把聚合条件写进 WHERE → 直接报错
SELECT basin,
    COUNT(*) AS 站数
FROM station
WHERE SUM(annual_flow) >= 300
GROUP BY basin;
-- 三表连接：流域 → 站点 → 河流，每行 = 流域×站×河 的组合
SELECT b.basin_name,
    COUNT(s.id) AS 站数,
    ROUND(SUM(s.annual_flow), 1) AS 总流量
FROM basin b
    LEFT JOIN station s ON s.basin = b.basin_name
    LEFT JOIN river r ON r.basin_name = b.basin_name
GROUP BY b.basin_name;
--先聚合，再连接
SELECT b.basin_name,
    COALESCE(s.站数, 0) AS 站数,
    COALESCE(s.总流量, 0) AS 总流量
FROM basin b
    LEFT JOIN (
        SELECT basin,
            COUNT(*) AS 站数,
            SUM(annual_flow) AS 总流量
        FROM station
        GROUP BY basin
    ) s ON s.basin = b.basin_name;