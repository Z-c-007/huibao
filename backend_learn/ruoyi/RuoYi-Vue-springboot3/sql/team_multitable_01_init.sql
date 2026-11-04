-- 北三县“运维关系配置”多表练习：01 建表和准备数据
-- 业务依据：direction/项目沉淀/北三县/项目功能全景_2026-10-31.md，运维关系配置。
-- 这是MySQL 8.0教学模型，非北三县PostgreSQL原始表结构。
-- 六张表均使用learn_ops_前缀。模拟用户表只放人员资料，不参与若依登录。
-- DBeaver：使用有建表权限的账号连接ry-vue；整份脚本Alt+X，单条完整SQL用Ctrl+Enter。
-- 本文件首次执行一次即可；重复INSERT会提示主键重复，此时不要删库或清表。
USE `ry-vue`;

-- 1. 人员：真实系统会读取已有用户资料，这里建立独立练习数据。
CREATE TABLE IF NOT EXISTS learn_ops_user (
    user_id BIGINT NOT NULL PRIMARY KEY COMMENT '人员编号',
    user_name VARCHAR(50) NOT NULL COMMENT '账号标识',
    nick_name VARCHAR(50) NOT NULL COMMENT '姓名',
    status CHAR(1) NOT NULL DEFAULT '0' COMMENT '0正常，1停用',
    UNIQUE KEY uk_learn_ops_user_name (user_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='练习：人员资料';

-- 2. 标段。
CREATE TABLE IF NOT EXISTS learn_ops_section (
    section_id BIGINT NOT NULL PRIMARY KEY COMMENT '标段编号',
    section_name VARCHAR(50) NOT NULL COMMENT '标段名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='练习：工程标段';

-- 3. 班组：班长是已有用户；成员关系另存。
-- 空班组允许暂不配置班长。非空班组“班长必须为有效成员”由业务保存流程检查。
CREATE TABLE IF NOT EXISTS learn_ops_team (
    team_id BIGINT NOT NULL PRIMARY KEY COMMENT '班组编号',
    team_name VARCHAR(100) NOT NULL COMMENT '班组名称',
    leader_user_id BIGINT DEFAULT NULL COMMENT '班长人员编号',
    phone VARCHAR(30) DEFAULT NULL COMMENT '联系电话',
    UNIQUE KEY uk_learn_ops_team_name (team_name),
    CONSTRAINT fk_learn_ops_team_leader FOREIGN KEY (leader_user_id)
        REFERENCES learn_ops_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='练习：巡检班组';

-- 4. 阀井：一口井属于一个标段，也允许暂未分配标段。
CREATE TABLE IF NOT EXISTS learn_ops_well (
    well_id BIGINT NOT NULL PRIMARY KEY COMMENT '阀井编号',
    well_code VARCHAR(30) NOT NULL COMMENT '业务编码',
    well_name VARCHAR(100) NOT NULL COMMENT '名称',
    section_id BIGINT DEFAULT NULL COMMENT '标段编号',
    status CHAR(1) NOT NULL DEFAULT '0' COMMENT '0启用，1停用',
    UNIQUE KEY uk_learn_ops_well_code(well_code),
    CONSTRAINT fk_learn_ops_well_section FOREIGN KEY(section_id)
        REFERENCES learn_ops_section(section_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='练习：阀井台账';

-- 5. 班组成员关系：复合主键防止同一关系重复；user_id唯一表示每个人最多属于一个班组。
CREATE TABLE IF NOT EXISTS learn_ops_team_member (
    team_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY(team_id, user_id),
    UNIQUE KEY uk_learn_ops_member_user(user_id),
    CONSTRAINT fk_learn_ops_member_team FOREIGN KEY(team_id)
        REFERENCES learn_ops_team(team_id),
    CONSTRAINT fk_learn_ops_member_user FOREIGN KEY(user_id)
        REFERENCES learn_ops_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='练习：班组成员关系';

-- 6. 班组负责阀井关系：well_id唯一表示一口井最多由一个班组负责。
CREATE TABLE IF NOT EXISTS learn_ops_team_well (
    team_id BIGINT NOT NULL,
    well_id BIGINT NOT NULL,
    PRIMARY KEY(team_id, well_id),
    UNIQUE KEY uk_learn_ops_team_well_well(well_id),
    CONSTRAINT fk_learn_ops_tw_team FOREIGN KEY(team_id)
        REFERENCES learn_ops_team(team_id),
    CONSTRAINT fk_learn_ops_tw_well FOREIGN KEY(well_id)
        REFERENCES learn_ops_well(well_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='练习：班组负责阀井关系';

-- 本教学模型使用物理外键，便于直接在DBeaver演示非法关系被拒绝。
-- 沉淀文档记载北三县跨模块关系由服务层校验，不能据此说真实项目也用了这些外键。

INSERT INTO learn_ops_user(user_id,user_name,nick_name,status) VALUES
(1001,'zhangsan','张三','0'),
(1002,'lisi','李四','0'),
(1003,'wangwu','王五','0'),
(1004,'zhaoliu','赵六','0'),
(1005,'disabled_user','停用人员','1');

INSERT INTO learn_ops_section(section_id,section_name) VALUES
(10,'一标段'),(20,'二标段');

INSERT INTO learn_ops_team(team_id,team_name,leader_user_id,phone) VALUES
(1,'一班',1001,'13800000001'),
(2,'二班',1003,'13800000002'),
(3,'三班',NULL,NULL);

INSERT INTO learn_ops_well(well_id,well_code,well_name,section_id,status) VALUES
(2001,'FJ001','人民路一号阀井',10,'0'),
(2002,'FJ002','人民路二号阀井',20,'0'),
(2003,'FJ003','滨河路阀井',10,'0'),
(2004,'FJ004','新建道路阀井',NULL,'0');

INSERT INTO learn_ops_team_member(team_id,user_id) VALUES
(1,1001),(1,1002),(2,1003);

INSERT INTO learn_ops_team_well(team_id,well_id) VALUES
(1,2001),(1,2002),(2,2003);

-- 成功后：一班2人2井，二班1人1井，三班0人0井。
-- 赵六未分组；FJ004未被班组负责，供后续修改练习使用。
SELECT * FROM learn_ops_team ORDER BY team_id;
SELECT * FROM learn_ops_team_member ORDER BY team_id,user_id;
SELECT * FROM learn_ops_team_well ORDER BY team_id,well_id;
