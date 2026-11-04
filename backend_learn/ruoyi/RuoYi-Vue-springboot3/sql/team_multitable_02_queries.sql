-- 北三县“运维关系配置”多表练习：02 查询（全部只读，可重复执行）
USE `ry-vue`;

-- 【A】先看六张表分别保存什么。每次选择一条完整SELECT按Ctrl+Enter。
SELECT * FROM learn_ops_user ORDER BY user_id;
SELECT * FROM learn_ops_section ORDER BY section_id;
SELECT * FROM learn_ops_team ORDER BY team_id;
SELECT * FROM learn_ops_well ORDER BY well_id;
SELECT * FROM learn_ops_team_member ORDER BY team_id,user_id;
SELECT * FROM learn_ops_team_well ORDER BY team_id,well_id;

-- 【B】刻意展示“展开的明细”，不是正确的班组摘要。
-- 一班：2个成员 × 2口井 = 4行。不是数据库多了4个班组。
SELECT t.team_id,t.team_name,u.nick_name,w.well_code,s.section_name
FROM learn_ops_team t
LEFT JOIN learn_ops_team_member tm ON tm.team_id=t.team_id
LEFT JOIN learn_ops_user u ON u.user_id=tm.user_id
LEFT JOIN learn_ops_team_well tw ON tw.team_id=t.team_id
LEFT JOIN learn_ops_well w ON w.well_id=tw.well_id
LEFT JOIN learn_ops_section s ON s.section_id=w.section_id
WHERE t.team_id=1
ORDER BY u.user_id,w.well_id;

-- 【C】错误统计示范：SQL合法，但业务结果不对。
-- 一班成员数4、阀井数4，实际应当各2；用于对比，不要作为接口实现。
SELECT t.team_id,t.team_name,
       COUNT(tm.user_id) AS wrong_member_count,
       COUNT(tw.well_id) AS wrong_well_count
FROM learn_ops_team t
LEFT JOIN learn_ops_team_member tm ON tm.team_id=t.team_id
LEFT JOIN learn_ops_team_well tw ON tw.team_id=t.team_id
GROUP BY t.team_id,t.team_name
ORDER BY t.team_id;

-- 【D】正确的班组摘要：每一行只代表一个班组。
-- 先分别按班组汇总两组一对多关系，再关联，避免明细互相组合。
-- 成员数口径：全部已关联人员（包括停用人员）；阀井数：全部已关联阀井。
-- LEFT JOIN保留空班组；COALESCE把没有统计结果的NULL显示为0。
SELECT t.team_id,t.team_name,
       COALESCE(leader.nick_name,'暂未配置') AS leader_name,
       COALESCE(mc.member_count,0) AS member_count,
       COALESCE(wc.well_count,0) AS well_count,
       COALESCE(wc.section_names,'暂未分配') AS section_names
FROM learn_ops_team t
LEFT JOIN learn_ops_user leader ON leader.user_id=t.leader_user_id
LEFT JOIN (
    SELECT team_id,COUNT(*) AS member_count
    FROM learn_ops_team_member GROUP BY team_id
) mc ON mc.team_id=t.team_id
LEFT JOIN (
    SELECT tw.team_id,COUNT(*) AS well_count,
           GROUP_CONCAT(DISTINCT s.section_name ORDER BY s.section_name SEPARATOR '、') AS section_names
    FROM learn_ops_team_well tw
    JOIN learn_ops_well w ON w.well_id=tw.well_id
    LEFT JOIN learn_ops_section s ON s.section_id=w.section_id
    GROUP BY tw.team_id
) wc ON wc.team_id=t.team_id
ORDER BY t.team_id
LIMIT 10 OFFSET 0;
-- 预期：一班/张三/2/2/一标段、二标段；二班/王五/1/1/一标段；三班/暂未配置/0/0/暂未分配。
-- GROUP_CONCAT用于短摘要；完整阀井清单使用【F】，不依赖字符串拼接。

-- 【E】筛选“包含张三的班组”，但成员数仍统计完整班组，不能错误变成1。
-- EXISTS只判断这个班组是否包含人员1001，不缩小mc统计的成员范围。
SELECT t.team_id,t.team_name,COALESCE(mc.member_count,0) AS member_count,
       COALESCE(wc.well_count,0) AS well_count
FROM learn_ops_team t
LEFT JOIN (
    SELECT team_id,COUNT(*) AS member_count FROM learn_ops_team_member GROUP BY team_id
) mc ON mc.team_id=t.team_id
LEFT JOIN (
    SELECT team_id,COUNT(*) AS well_count FROM learn_ops_team_well GROUP BY team_id
) wc ON wc.team_id=t.team_id
WHERE EXISTS (
    SELECT 1 FROM learn_ops_team_member filter_member
    WHERE filter_member.team_id=t.team_id AND filter_member.user_id=1001
)
ORDER BY t.team_id
LIMIT 10 OFFSET 0;
-- 预期：一班，成员2人、阀井2口。

-- 筛选后总条数：与上面的主体筛选保持一致，数班组，不数关联明细。
SELECT COUNT(*) AS total
FROM learn_ops_team t
WHERE EXISTS (
    SELECT 1 FROM learn_ops_team_member tm WHERE tm.team_id=t.team_id AND tm.user_id=1001
);

-- 其他筛选条件示范：负责FJ001的班组。
SELECT t.team_id,t.team_name
FROM learn_ops_team t
WHERE EXISTS (
    SELECT 1 FROM learn_ops_team_well tw
    JOIN learn_ops_well w ON w.well_id=tw.well_id
    WHERE tw.team_id=t.team_id AND w.well_code='FJ001'
);

-- 【F】班组详情：一个业务接口可以执行下面3次查询，再组装成一个对象。
-- 这不是N+1：查询次数固定为3次，不是查N条后循环每条再查。
-- F1 主信息。
SELECT t.team_id,t.team_name,t.phone,t.leader_user_id,u.nick_name AS leader_name
FROM learn_ops_team t
LEFT JOIN learn_ops_user u ON u.user_id=t.leader_user_id
WHERE t.team_id=1;

-- F2 成员列表。
SELECT u.user_id,u.user_name,u.nick_name,u.status,
       CASE WHEN u.user_id=t.leader_user_id THEN '班长' ELSE '成员' END AS team_role
FROM learn_ops_team_member tm
JOIN learn_ops_user u ON u.user_id=tm.user_id
JOIN learn_ops_team t ON t.team_id=tm.team_id
WHERE tm.team_id=1 ORDER BY u.user_id;

-- F3 负责阀井列表。
SELECT w.well_id,w.well_code,w.well_name,w.status,s.section_name
FROM learn_ops_team_well tw
JOIN learn_ops_well w ON w.well_id=tw.well_id
LEFT JOIN learn_ops_section s ON s.section_id=w.section_id
WHERE tw.team_id=1 ORDER BY w.well_id;

-- 【G】选择成员/阀井前的检查：尚未分组、且未停用的人员。
SELECT u.user_id,u.nick_name FROM learn_ops_user u
WHERE u.status='0' AND NOT EXISTS (
    SELECT 1 FROM learn_ops_team_member tm WHERE tm.user_id=u.user_id
);
-- 初始应只有赵六，不包含停用人员。

SELECT w.well_id,w.well_code FROM learn_ops_well w
WHERE w.status='0' AND NOT EXISTS (
    SELECT 1 FROM learn_ops_team_well tw WHERE tw.well_id=w.well_id
);
-- 初始应只有FJ004。
