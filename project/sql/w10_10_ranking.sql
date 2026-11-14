SELECT s.name AS street,
    d.name AS district,
    SUM(u.water_used) AS total_used,
    COUNT(*) AS user_count
FROM streets s
    JOIN districts d ON s.district_id = d.id
    JOIN water_users u ON ST_Within(u.geom, s.geom)
GROUP BY s.name,
    d.name
ORDER BY total_used DESC;