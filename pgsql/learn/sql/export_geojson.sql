-- export_geojson.sql —— 一次性导出 6 个图层文件
-- 官方文档方案：COPY (...) TO STDOUT + \g 文件路径
-- 来源：https://www.postgresql.org/docs/current/app-psql.html \copy 小节 Tip
\encoding UTF8

-- A 流域边界
COPY (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', jsonb_agg(jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geom)::jsonb,
            'properties', jsonb_build_object(
                'gid', gid,
                'area_km2', ROUND((ST_Area(geom::geography)/1e6)::numeric, 1)
            )
        ))
    ) AS geojson
    FROM hydrobasins WHERE gid = 611
) TO STDOUT
\g D:/GIS_learn/pgsql/learn/output/basin_boundary.geojson

-- B 河流
COPY (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', jsonb_agg(jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geom)::jsonb,
            'properties', jsonb_build_object(
                'gid', gid,
                'hyriv_id', hyriv_id,
                'main_riv', main_riv,
                'length_km', ROUND((ST_Length(geom::geography)/1000)::numeric, 1)
            )
        ))
    ) AS geojson
    FROM demo_basin_rivers
) TO STDOUT
\g D:/GIS_learn/pgsql/learn/output/basin_rivers.geojson

-- C 湖泊（面积分档）
COPY (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', jsonb_agg(jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(l.geom)::jsonb,
            'properties', jsonb_build_object(
                'gid', l.gid,
                'lake_name', COALESCE(NULLIF(l.name_zh, ''), l.name),
                'area_km2', ROUND((ST_Area(l.geom::geography)/1e6)::numeric, 1),
                'size_category', CASE
                    WHEN ST_Area(l.geom::geography)/1e6 > 100 THEN '大型'
                    WHEN ST_Area(l.geom::geography)/1e6 > 10  THEN '中型'
                    ELSE '小型'
                END
            )
        ))
    ) AS geojson
    FROM hydrolakes l
    JOIN hydrobasins b ON ST_Contains(b.geom, l.geom)
    WHERE b.gid = 611
) TO STDOUT
\g D:/GIS_learn/pgsql/learn/output/basin_lakes.geojson

-- D 管控区
COPY (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', jsonb_agg(jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geom)::jsonb,
            'properties', jsonb_build_object(
                'name', '5km生态管控区',
                'control_zone_km2', ROUND((ST_Area(geom::geography)/1e6)::numeric, 2)
            )
        ))
    ) AS geojson
    FROM demo_control_zone
) TO STDOUT
\g D:/GIS_learn/pgsql/learn/output/control_zone.geojson

-- E 叠加（被管控区压到的湖）
COPY (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', jsonb_agg(jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(l.geom)::jsonb,
            'properties', jsonb_build_object(
                'lake_name', o.lake_name,
                'lake_area_km2', o.lake_area_km2,
                'overlap_km2', o.overlap_km2,
                'cover_pct', ROUND((o.overlap_km2/NULLIF(o.lake_area_km2,0)*100)::numeric, 1)
            )
        ))
    ) AS geojson
    FROM demo_lake_overlay o
    JOIN hydrolakes l ON l.gid = o.gid
) TO STDOUT
\g D:/GIS_learn/pgsql/learn/output/lake_overlay.geojson

-- F 湖质心挂名
COPY (
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', jsonb_agg(jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(ST_Centroid(l.geom))::jsonb,
            'properties', jsonb_build_object(
                'gid', l.gid,
                'lake_name', COALESCE(NULLIF(l.name_zh, ''), l.name)
            )
        ))
    ) AS geojson
    FROM hydrolakes l
    JOIN hydrobasins b ON ST_Contains(b.geom, l.geom)
    WHERE b.gid = 611
) TO STDOUT
\g D:/GIS_learn/pgsql/learn/output/lake_centroids.geojson