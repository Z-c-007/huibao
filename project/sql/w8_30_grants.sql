-- w8_30_grants.sql ｜ ai_reader 最小权限授权 + 权限自检（超级用户执行）
\encoding UTF8
GRANT CONNECT ON DATABASE ai_water_budget TO ai_reader;
\c ai_water_budget
GRANT USAGE ON SCHEMA public TO ai_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ai_reader;

-- ===== 权限自检 =====
SET ROLE ai_reader;
SELECT COUNT(*) AS read_ok FROM water_users;   -- 期望：成功返回 4

INSERT INTO water_users (name, industry, water_used, budget, geom)
VALUES ('hack', '制造业', 1, 1, ST_SetSRID(ST_MakePoint(0, 0), 4326));
-- 期望：ERROR: permission denied for table water_users（报错后 psql 继续执行后续语句）
RESET ROLE;
