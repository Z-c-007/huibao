-- 阀井基础信息教学数据。先在数据库工具中选中项目配置的 ry-vue 数据库，再执行。
-- 不创建或切换数据库，不删除现有表，不覆盖已有同编号记录。
-- 表、列及约束针对本教学示例；若同名表已存在且结构不同，请先检查结构。
CREATE TABLE IF NOT EXISTS biz_valve_well (
    well_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '内部主键',
    well_code VARCHAR(32) NOT NULL COMMENT '阀井业务编号，例如 FJ001',
    well_name VARCHAR(100) NOT NULL COMMENT '阀井名称',
    location VARCHAR(255) NOT NULL COMMENT '位置文字描述',
    diameter INT NOT NULL COMMENT '阀门口径，单位毫米',
    status CHAR(1) NOT NULL DEFAULT '0' COMMENT '状态：0正常，1停用',
    PRIMARY KEY (well_id),
    UNIQUE KEY uk_valve_well_code (well_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='阀井基础信息（教学示例）';

-- INSERT 新增教学数据；NOT EXISTS 避免顺序重复执行脚本时重复插入同编号记录。
-- 不指定 well_id，由数据库自动生成，因此返回的 ID 不保证一定是 1 和 2。
INSERT INTO biz_valve_well (well_code, well_name, location, diameter, status)
SELECT 'FJ001', '人民路一号阀井', '人民路东段', 200, '0'
WHERE NOT EXISTS (SELECT 1 FROM biz_valve_well WHERE well_code = 'FJ001');

INSERT INTO biz_valve_well (well_code, well_name, location, diameter, status)
SELECT 'FJ002', '建设路二号阀井', '建设路南段', 150, '1'
WHERE NOT EXISTS (SELECT 1 FROM biz_valve_well WHERE well_code = 'FJ002');

-- 可单独执行以下查询，核对数据库里的原始数据与 HTTP 返回结果。
SELECT well_id, well_code, well_name, location, diameter, status
FROM biz_valve_well
ORDER BY well_id ASC;
