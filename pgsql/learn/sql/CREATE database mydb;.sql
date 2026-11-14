-- 1. 建表（跑一次，之后用选中执行跳过它）

CREATE TABLE IF NOT EXISTS mytable (id SERIAL PRIMARY KEY,
                                              name VARCHAR(30) NOT NULL,
                                                               email VARCHAR(50),
                                                                     reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

-- 2. 插数据（想重来就先 DROP TABLE，再回到这里跑）

INSERT INTO mytable (name, email)
VALUES ('Alice', 'alice@example.com'),
       ('Bob', 'bob@example.com');

-- 3. 查询（这个随便重复跑，不会改数据，安全）

SELECT *
FROM mytable;

-- 加列（你第 17 行写的，对的）

ALTER TABLE mytable ADD COLUMN age INT;

-- 改列类型（你想做的应该是这个，不是再 ADD 一次）

ALTER TABLE mytable
ALTER COLUMN age TYPE TEXT;

-- 删列

ALTER TABLE mytable
DROP COLUMN age;


UPDATE mytable
SET name = 'zcyyr'
WHERE id = 1;


DELETE
FROM mytable
WHERE id = 1;

-- 清空表的所有行，表结构保留

TRUNCATE TABLE mytable;

-- 清空 + 同时重置自增序列（SERIAL 的 id 从 1 重新开始）

TRUNCATE TABLE mytable RESTART IDENTITY;

-- 删掉 mytable（结构 + 数据全部删除）

DROP TABLE mytable;

-- 用 IF EXISTS，表不存在也不报错（推荐学习用）

DROP TABLE IF EXISTS mytable;

-- 级联删除：同时删掉依赖这个表的视图等

DROP TABLE mytable CASCADE;

-- 父表：所有城市

CREATE TABLE cities (name text, population real, elevation int);


SELECT *
FROM cities;

-- 子表：省会，继承 cities 的所有列 + 多了 state 列

CREATE TABLE capitals (state char(2) UNIQUE NOT NULL) INHERITS (cities);


SELECT *
FROM capitals;