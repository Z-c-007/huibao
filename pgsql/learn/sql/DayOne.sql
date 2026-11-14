CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(30),
    dept_id INT
);
-- DROP TABLE empplyess CASCADE;
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    dept_name VARCHAR(30)
);
INSERT INTO employees (name, dept_id)
VALUES ('Jane', 1),
    ('Jim', 2),
    ('Jack', 3),
    ('Jill', NULL);
INSERT INTO departments (id, dept_name)
VALUES (1, '水利信息化部'),
    (2, 'GIS研发部'),
    (3, '无人部门');
-- SELECT *
SELECT *
FROM departments;
-- 写法 A：显式 CROSS JOIN
SELECT e.name,
    e.dept_id,
    d.dept_name,
    d.id
FROM employees e
    CROSS JOIN departments d;
-- 写法 B：逗号语法（老写法，PostGIS 教程常见
SELECT e.name,
    d.dept_name
FROM employees e,
    departments d;
-- 写法 C：INNER JOIN ... ON TRUE（CROSS 的等价形式
SELECT e.name,
    d.dept_name
FROM employees e
    INNER JOIN departments d ON TRUE;
3.验证行数
SELECT COUNT(*)
FROM employees
    CROSS JOIN departments;
SELECT e.name,
    d.dept_name
FROM employees e
    INNER JOIN departments d ON e.dept_id = d.id;
SELECT name,
    dept_id
FROM employees
WHERE name = 'Jill';
ALTER TABLE departments
ADD COLUMN name VARCHAR(30);
UPDATE departments
SET name = dept_name;
SELECT *
FROM departments;
SELECT name
FROM employees e
    INNER JOIN departments d ON e.dept_id = d.id;
-- 限定列名 → 正常
SELECT e.name AS 员工,
    d.name AS 部门
FROM employees e
    INNER JOIN departments d ON e.dept_id = d.id;
ALTER TABLE departments DROP COLUMN name;
SELECT e.name,
    d.dept_name
FROM employees e
    JOIN departments d ON e.dept_id = d.id;
SELECT 1 = 1 AS "1等于1",
    1 = NULL AS "1等于NULL",
    NULL = NULL AS "NULL等于NULL";
SELECT e.name,
    d.dept_name
FROM employees e
    LEFT JOIN departments d ON e.dept_id = d.id;
SELECT e.name,
    d.dept_name
FROM employees e
    RIGHT JOIN departments d ON e.dept_id = d.id;
SELECT e.name,
    d.dept_name
FROM employees e
    FULL JOIN departments d ON e.dept_id = d.id;
SELECT e.name
FROM employees e
    LEFT JOIN departments d ON e.dept_id = d.id
WHERE d.id IS NULL;
INSERT INTO departments (id, dept_name)
VALUES (4, '新无人部门');
SELECT d.dept_name
FROM employees e
    RIGHT JOIN departments d ON e.dept_id = d.id
WHERE e.id IS NULL;
-- 正确写法：过滤条件放进 ON，LEFT JOIN 保留所有员工
SELECT e.name,
    d.dept_name
FROM employees e
    LEFT JOIN departments d ON e.dept_id = d.id
WHERE d.id = 2;
-- 正确写法：过滤条件放进 ON，LEFT JOIN 保留所有员工
SELECT e.name,
    d.dept_name
FROM employees e
    LEFT JOIN departments d ON e.dept_id = d.id
    AND d.id = 2;
------------
INSERT INTO employees (name, dept_id)
VALUES ('新员工A', 1),
    ('新员工B', 1);
SELECT *
FROM employees;
SELECT e1.name AS 员工1,
    e2.name AS 员工2
FROM employees e1
    INNER JOIN employees e2 ON e1.dept_id = e2.dept_id
    AND e1.id < e2.id
ORDER BY e1.dept_id;
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    proj_name VARCHAR(50),
    emp_id INT
);
INSERT INTO projects (proj_name, emp_id)
VALUES ('洪水淹没分析', 1),
    ('水质监测大屏', 1),
    ('河长制平台', 2);
SELECT *
FROM projects;
SELECT e.name,
    d.dept_name,
    p.proj_name
FROM employees e
    INNER JOIN departments d ON e.dept_id = d.id
    LEFT JOIN projects p ON e.id = p.emp_id
ORDER BY e.id;
SELECT d.dept_name,
    COUNT(*) AS 行数,
    -- 被项目放大过的伪计数
    COUNT(p.id) AS 项目数
FROM employees e
    INNER JOIN departments d ON e.dept_id = d.id
    LEFT JOIN projects p ON e.id = p.emp_id
GROUP BY d.dept_name;
-- 正确：用 COUNT(DISTINCT ...) 或 COUNT(e.id)
SELECT d.dept_name,
    COUNT(DISTINCT e.id) AS 真实员工数,
    COUNT(p.id) AS 项目数
FROM employees e
    INNER JOIN departments d ON e.dept_id = d.id
    LEFT JOIN projects p ON e.id = p.emp_id
GROUP BY d.dept_name;
-- USING 要求连接列两边同名，建两张列名一致的练习表
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT,
    amount NUMERIC
);
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(30)
);
INSERT INTO customers (id, customer_name)
VALUES (1, '河务局'),
    (2, '水文局'),
    (3, '设计院');
INSERT INTO orders (customer_id, amount)
VALUES (1, 100.5),
    (1, 200.0),
    (2, 350.25);
SELECT *
FROM customers;
SELECT *
FROM orders;
-- 把 orders 的连接列改名为 id，让两边都有 id
-- ALTER TABLE orders
--     RENAME COLUMN customer_id TO id;
SELECT c.customer_name,
    o.amount
FROM customers c
    INNER JOIN orders o USING (id);
-- NATURAL = 自动匹配"所有同名列"（这里会匹配 id），等价于 USING(id)
SELECT c.customer_name,
    o.amount
FROM customers c NATURAL
    INNER JOIN orders o;