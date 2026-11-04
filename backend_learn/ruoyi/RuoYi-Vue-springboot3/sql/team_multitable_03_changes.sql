-- 北三县“运维关系配置”多表练习：03 多表写入与关系修改
-- 默认每个演示都以ROLLBACK结束，方便重复练习；要保留才将对应ROLLBACK改成COMMIT。
-- 同一事务在同一个连接里执行；出现错误立即执行ROLLBACK，不继续后续写入。
-- 下列是可观察的数据操作步骤；生产代码还需在Service中检查权限、输入完整性、状态及影响行数。
USE `ry-vue`;

-- 【H】新增班组，同时指定班长、成员、负责阀井：一次业务操作写3张表。
-- 初始数据中赵六1004、FJ004/2004均未分配；先在02文件【G】确认。
START TRANSACTION;
SELECT * FROM learn_ops_user WHERE user_id=1004 AND status='0' FOR UPDATE;
SELECT * FROM learn_ops_well WHERE well_id=2004 AND status='0' FOR UPDATE;
-- 检查已有关系，预期均0行；非0行则ROLLBACK，不能再分配。
SELECT * FROM learn_ops_team_member WHERE user_id=1004;
SELECT * FROM learn_ops_team_well WHERE well_id=2004;

INSERT INTO learn_ops_team(team_id,team_name,leader_user_id,phone)
VALUES(4,'四班',1004,'13800000004');
INSERT INTO learn_ops_team_member(team_id,user_id) VALUES(4,1004);
INSERT INTO learn_ops_team_well(team_id,well_id) VALUES(4,2004);
SELECT * FROM learn_ops_team WHERE team_id=4;
SELECT * FROM learn_ops_team_member WHERE team_id=4;
SELECT * FROM learn_ops_team_well WHERE team_id=4;
ROLLBACK;

-- 【I】全量替换一班成员：张三、李四 → 张三、赵六。
-- 删除的是关联关系，不删除人员；班长张三仍包含在完整名单中。
START TRANSACTION;
SELECT * FROM learn_ops_team WHERE team_id=1 FOR UPDATE;
SELECT * FROM learn_ops_user WHERE user_id IN (1001,1004) ORDER BY user_id FOR UPDATE;
-- 两个用户必须都存在且status=0，人员冲突检查应返回0行，否则ROLLBACK。
SELECT * FROM learn_ops_team_member WHERE user_id IN (1001,1004) AND team_id<>1;
DELETE FROM learn_ops_team_member WHERE team_id=1;
INSERT INTO learn_ops_team_member(team_id,user_id) VALUES(1,1001),(1,1004);
SELECT tm.team_id,u.user_id,u.nick_name FROM learn_ops_team_member tm
JOIN learn_ops_user u ON u.user_id=tm.user_id WHERE tm.team_id=1;
SELECT * FROM learn_ops_user WHERE user_id=1002;
-- 李四这个人仍存在，只是没有一班成员关系。回滚后原成员关系也恢复。
ROLLBACK;

-- 【J】全量替换一班负责阀井：FJ001、FJ002 → FJ001、FJ004。
START TRANSACTION;
SELECT * FROM learn_ops_team WHERE team_id=1 FOR UPDATE;
SELECT * FROM learn_ops_well WHERE well_id IN (2001,2004) ORDER BY well_id FOR UPDATE;
-- 两口井必须都存在且status=0，冲突检查应0行，否则ROLLBACK。
SELECT * FROM learn_ops_team_well WHERE well_id IN (2001,2004) AND team_id<>1;
DELETE FROM learn_ops_team_well WHERE team_id=1;
INSERT INTO learn_ops_team_well(team_id,well_id) VALUES(1,2001),(1,2004);
SELECT tw.team_id,w.well_code FROM learn_ops_team_well tw
JOIN learn_ops_well w ON w.well_id=tw.well_id WHERE tw.team_id=1;
SELECT * FROM learn_ops_well WHERE well_id=2002;
-- FJ002仍存在；默认回滚，保留初始负责关系。
ROLLBACK;

-- 【K】故意触发冲突，观察数据库唯一约束如何兜底。
-- 一条一条执行：FJ003已经属于二班，再分配给一班应提示重复键。
-- 出错后事务不会因为这一个普通SQL错误就自动全部回滚，要主动执行最后的ROLLBACK。
START TRANSACTION;
INSERT INTO learn_ops_team_well(team_id,well_id) VALUES(1,2003);
ROLLBACK;

-- 【L】本练习仅删除没有成员、没有负责阀井的空班组；此处三班是空班组。
-- 有历史巡检时的保留规则留到后续巡检练习，六表模型尚不包含历史任务表。
START TRANSACTION;
SELECT * FROM learn_ops_team WHERE team_id=3 FOR UPDATE;
SELECT * FROM learn_ops_team_member WHERE team_id=3;
SELECT * FROM learn_ops_team_well WHERE team_id=3;
-- 两个关联查询都为0行，才执行删除。
DELETE FROM learn_ops_team WHERE team_id=3;
SELECT * FROM learn_ops_team WHERE team_id=3;
ROLLBACK;
