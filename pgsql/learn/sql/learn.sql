-- 1. 建父表：所有员工

CREATE TABLE employees (id SERIAL PRIMARY KEY,
                                  name VARCHAR(30) NOT NULL,
                                                   salary INT);


SELECT *
FROM employees;

-- 2. 建子表：开发人员，继承 employees + 多一个语言列

CREATE TABLE developers (language VARCHAR(20)) INHERITS (employees);


SELECT *
FROM developers;

-- 3. 建另一个子表：设计师，继承 employees + 多一个工具列

CREATE TABLE designers (tool VARCHAR(20)) INHERITS (employees);


SELECT *
FROM designers;

-- 4. 分别往子表插入数据

INSERT INTO developers (name, salary, language)
VALUES ('Alice', 80000, 'Python'),
       ('Bob', 75000, 'Go');


INSERT INTO designers (name, salary, tool)
VALUES ('Carol', 70000, 'Figma'),
       ('Dave', 65000, 'Photoshop');


INSERT INTO employees (name, salary)
VALUES ('Eve', 50000);


SELECT *
FROM ONLY employees;


SELECT tableoid::regclass,
       name,
       salary
FROM employees;
