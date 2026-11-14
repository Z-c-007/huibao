-- ============================================================
-- Day 13：Geography 类型 —— 跨省/跨国的量算，一条路走球面
-- 库：day3_pra ｜ 表：hydrorivers / hydrobasins / hydrolakes（SRID=4326）
-- 官方依据：PostGIS Workshop §18-19；PostGIS 手册 ST_Distance / ST_DWithin / ST_Buffer / ST_Area / ST_Length（geography 变体）
-- ============================================================

-- ------------------------------------------------------------
-- 一、业务背景
-- 业务方：水利部信息中心"全国河湖库监测一张图"防汛组。
-- 需求：入汛后以各省上报的水文/雨量站为圆心，圈出周边 100~200km 范围内所有湖库，
--       做跨省跨流域暴雨影响评估（如"北京站 100km 内有哪些水库，官厅水库蓄水情况如何"）。
-- 数据全部是各省汇交的 WGS84(4326) 经纬度。
-- 为什么必须用 geography：这种分析经常跨省、跨流域甚至跨国（北京→乌鲁木齐 2400km+）。
--   用 4326 geometry 算距离得到的是"度"（无物理意义）；
--   用投影（4527/3857）只覆盖局部带，跨带误差大且要逐带判断。
--   geography 直接在 WGS84 椭球面上算大圆距离，米制、精确、跨带无忧——
--   正好接 Day 12 留下的"全球/大尺度用 geography 一条路"。
-- ------------------------------------------------------------

-- ============================================================
-- 练习 0：建演示表（真库还没有 stations，先建）
-- ============================================================
-- geometry(Point, 4326)：限定空间列类型 = 点 + SRID 4326。
-- ST_SetSRID(ST_MakePoint(经, 纬), 4326)：造一个 4326 的点。
-- DROP + CREATE：让整个文件可重复执行（重复跑 INSERT 不会攒出重复站点）。
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

-- ============================================================
-- 练习 1：geometry vs geography 距离对比（北京 → 上海）
-- ============================================================
-- 同一个点对，两种类型：
--   geometry 下算距离，单位是"度"（10.08 度，无物理意义）；
--   geography 下算距离，单位是米（1069.8 km，才是真的）。
SELECT ST_Distance(a, b) AS geom_dist_deg,                          -- 10.08，度，无意义
       ROUND((ST_Distance(a::geography, b::geography) / 1000)::numeric, 1) AS geog_dist_km  -- 1069.8
FROM (
        SELECT ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326) a,
               ST_SetSRID(ST_MakePoint(121.5, 31.2), 4326) b
    ) t;
-- 预期：
-- | geom_dist_deg | geog_dist_km |
-- |--------------:|-------------:|
-- | 10.0846417... | 1069.8       |

-- ============================================================
-- 练习 2：CAST 两种写法等价（:: 和 CAST 完全一样）
-- ============================================================
-- 显式 JOIN（模板强制项 #6，新代码不用逗号语法）。
-- 两行只用来演示等价性：d1_km 和 d2_km 应完全相同。
SELECT ST_Distance(s1.geom::geography, s2.geom::geography) / 1000 AS d1_km,
       ST_Distance(
           CAST(s1.geom AS geography),
           CAST(s2.geom AS geography)
       ) / 1000 AS d2_km
FROM stations s1
JOIN stations s2 ON s1.name = '北京站' AND s2.name = '上海站';
-- 预期：d1_km = d2_km = 1069.8

-- ============================================================
-- 练习 3：业务核心——北京站 200km 内所有湖库（本日交付）
-- ============================================================
-- ST_DWithin(l.geom::geography, s.geom::geography, 200000)：布尔谓词，
-- 问"湖和站的最短球面距离 ≤ 200000 米（200km）吗"，只做筛选、不生成几何。
-- ST_Distance(...)/1000 算真实距离 km 用于排序展示。
SELECT l.gid,
    l.name,
    l.name_zh,
    ROUND((ST_Distance(l.geom::geography, s.geom::geography) / 1000)::numeric, 1) AS dist_km
FROM hydrolakes l
JOIN stations s ON s.name = '北京站'
WHERE ST_DWithin(l.geom::geography, s.geom::geography, 200000)  -- 200km（米）
ORDER BY dist_km;
-- 预期（真库实测命中 2 个）：
-- | gid  | name               | name_zh   | dist_km |
-- |------|--------------------|-----------|--------:|
-- | 1223 | Guanting Shuiku    | 官厅水库   |    74.1 |
-- | 1251 | Baidagang Shuiku   | 北大港水库 |   150.4 |

-- ============================================================
-- 练习 4：站点两两距离矩阵（自连接 + 显式 JOIN）
-- ============================================================
-- 教学用途：用 SQL 集合思维代替编程双重 for 循环，一次拿到"任意两站距离"。
-- a.name < b.name：去掉自己到自己的对角线，且每对只保留一次
--                  （5 站 → 全组合 25 行 → 去重后 10 行）。
-- 注意：生产不会对全国几千个站裸跑全量两两矩阵（O(N²)），见沉淀 Q1。
SELECT a.name AS from_st,
    b.name AS to_st,
    ROUND((ST_Distance(a.geom::geography, b.geom::geography) / 1000)::numeric, 1) AS dist_km
FROM stations a
JOIN stations b ON a.name < b.name  -- 去掉对角线 + 去重组合
ORDER BY a.name, dist_km;
-- 预期（真库实测 10 行，摘录）：
-- | from_st | to_st      | dist_km |
-- |---------|------------|--------:|
-- | 北京站   | 武汉站     |  1049.3 |
-- | 北京站   | 上海站     |  1069.8 |
-- | 北京站   | 广州站     |  1885.6 |
-- | 北京站   | 乌鲁木齐站 |  2417.9 |
-- | ...     | ...        |    ...  |

-- ============================================================
-- 练习 5：geography 米制 Buffer —— 每个站 100km 覆盖圈面积
-- ============================================================
-- 注意：这里是"造几何 + 算面积"，与练习 3 的"只判断"不同（见沉淀 Q2 Buffer vs DWithin）。
-- ST_Buffer(s.geom::geography, 100000)：geography 版缓冲，单位固定米，返回球面圆面。
-- ST_Area(...)/1e6：对球面圆面求面积 m² → km²。
SELECT s.name,
    ROUND((ST_Area(ST_Buffer(s.geom::geography, 100000)) / 1e6)::numeric, 1) AS cover_km2
FROM stations s
ORDER BY s.name;
-- 预期（真库实测，约 31200 km² ≈ π×100² = 31416，球面略小，合理）：
-- | name      | cover_km2 |
-- |-----------|----------:|
-- | 北京站     |   31235.5 |
-- | 广州站     |   31194.7 |
-- | 上海站     |   31221.8 |
-- | 乌鲁木齐站 |   31235.8 |
-- | 武汉站     |   31185.9 |

-- ============================================================
-- 练习 6：每个站周边 300km 湖库数 + 最近湖距离（聚合 + geography）
-- ============================================================
-- LEFT JOIN：站没有湖也保留（值为 0/NULL），防"站被静默丢掉"。
-- COUNT(l.gid)：只数匹配到的湖；MIN(ST_Distance(...))：最近的那个湖多远。
SELECT s.name,
    COUNT(l.gid) AS lake_cnt,
    ROUND((MIN(ST_Distance(l.geom::geography, s.geom::geography)) / 1000)::numeric, 1) AS nearest_km
FROM stations s
LEFT JOIN hydrolakes l ON ST_DWithin(l.geom::geography, s.geom::geography, 300000)  -- 300km
GROUP BY s.name
ORDER BY lake_cnt DESC;
-- 预期（真库实测）：
-- | name      | lake_cnt | nearest_km |
-- |-----------|---------:|-----------:|
-- | 武汉站     |       34 |        5.5 |
-- | 上海站     |        8 |       64.3 |
-- | 北京站     |        2 |       74.1 |
-- | 广州站     |        1 |      132.3 |
-- | 乌鲁木齐站 |        1 |      195.4 |

-- ============================================================
-- 练习 7：性能坑——geom::geography 谓词不走 geometry 索引 + 解法
-- ============================================================
-- 坑：ST_DWithin(geom::geography, ...) 里空间列被 ::geography 包裹成"表达式"，
--     Day 10 结论：函数包裹列 → 索引作废。真库实测走 Seq Scan 全表扫 ~329ms。
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM hydrolakes l
WHERE ST_DWithin(l.geom::geography, ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)::geography, 300000);
-- 实测：Seq Scan on hydrolakes，全表 1355 行，~329ms（没命中 hydrolakes_geom_idx）

-- 解法：建 geography 表达式 GiST 索引。
-- ⚠️ 表达式索引必须把整个表达式用【双重括号】包起来：
--    错：USING GIST (geom::geography)        → 语法错误 在 "::" 或附近
--    对：USING GIST ((geom::geography))      → 一个括号给列清单，一个给表达式
CREATE INDEX IF NOT EXISTS hydrolakes_geom_geog_idx ON hydrolakes USING GIST ((geom::geography));

-- 建完再 EXPLAIN 验证：应走 Index Scan using hydrolakes_geom_geog_idx，~27ms（约快 12 倍）
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM hydrolakes l
WHERE ST_DWithin(l.geom::geography, ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)::geography, 300000);
-- 实测：Index Scan using hydrolakes_geom_geog_idx，~26.7ms

-- ============================================================
-- 练习 8：综合交付——全站"跨省湖库影响评估"GeoJSON 输出（接 Day 16）
-- ============================================================
-- 每个站输出成一个 Feature：点坐标 + name + 100km 覆盖面积。
-- ST_AsGeoJSON(s.geom)：4326 点 → GeoJSON，前端直接画。
SELECT jsonb_build_object(
        'type',
        'FeatureCollection',
        'features',
        jsonb_agg(
            jsonb_build_object(
                'type',
                'Feature',
                'geometry',
                ST_AsGeoJSON(s.geom)::jsonb,
                'properties',
                jsonb_build_object(
                    'name',
                    s.name,
                    'cover_km2',
                    ROUND((ST_Area(ST_Buffer(s.geom::geography, 100000)) / 1e6)::numeric, 1)
                )
            )
        )
    ) AS geojson
FROM stations s;
-- 预期：一条 FeatureCollection，5 个 Point Feature，coordinates 是经纬度，cover_km2 ≈ 31200

-- ============================================================
-- 五、错误与陷阱（故意跑错，看后果）
-- ============================================================

-- 陷阱 1：geometry 距离是"度"——静默错误（能跑通但单位无意义）
-- 北京→上海返回 10.08，你以为"10.08"，实际单位是"度"，不是 km
SELECT ST_Distance(
        ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326),
        ST_SetSRID(ST_MakePoint(121.5, 31.2), 4326)
    ) AS deg_dist;
-- 正确：::geography 得到 1069.8 km

-- 陷阱 2：4326 geometry 下 ST_Buffer(geom, 50000) —— 静默错误
-- 50000 是"度"不是"米"，造出天文数字面积
SELECT ROUND((ST_Area(
        ST_Buffer(ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326), 50000)
    ))::numeric, 2) AS absurd_deg2;
-- 实测：7,803,612,880.65 平方度（离谱，不报错）
-- 正确：ST_Buffer(ST_SetSRID(...)::geography, 50000) 单位才是米

-- 陷阱 3：对 geography 直接 ST_Transform —— 报错
SELECT ST_Transform(ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)::geography, 4527);
-- 报错：函数 st_transform(geography, integer) 不存在
-- 原因：geography 已固定 WGS84 椭球，不需要（也不能）投影转换；
--       要投影先 cast 回 geometry：ST_Transform(geom::geometry, 4527)

-- 陷阱 4：geography 表达式索引漏掉双重括号 —— 报错
CREATE INDEX bad_idx ON hydrolakes USING GIST (geom::geography);
-- 报错：语法错误 在 "::" 或附近
-- 修正：USING GIST ((geom::geography))，表达式要整体包在括号里

-- ============================================================
-- 自检题（口头能答出 = 过关，详见沉淀 Day13 文档）
-- 独立练习：见沉淀 Day13 文档第九节
-- ============================================================
