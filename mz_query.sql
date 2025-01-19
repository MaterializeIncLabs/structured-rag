WITH clusters AS (
    SELECT name || ' is a ' || size || ' managed cluster with replication factor ' || replication_factor AS description
    FROM mz_catalog.mz_clusters
    WHERE id LIKE 'u%' AND managed IS TRUE
),

sources AS (
	SELECT s.name || ' is a ' || s.type || ' source on the ' || c.name || ' cluster' AS description
	FROM mz_catalog.mz_sources s
	JOIN mz_catalog.mz_clusters c ON s.cluster_id = c.id
	WHERE s.id LIKE 'u%' AND s.type NOT IN ('progress', 'subsource', 'table')
),

subsource_tables AS (
    SELECT 
        CASE 
            WHEN mz_sources.type = 'subsource' THEN 
                mz_sources.name || ' is a subsource of ' || parent_sources.name
            WHEN mz_sources.type = 'table' THEN 
                mz_sources.name || ' is a table built off ' || parent_sources.name
        END AS description
    FROM mz_internal.mz_object_dependencies AS deps
    JOIN mz_catalog.mz_sources AS mz_sources 
        ON mz_sources.id = deps.object_id
    JOIN mz_catalog.mz_sources AS parent_sources 
        ON parent_sources.id = deps.referenced_object_id
    WHERE parent_sources.type <> 'subsource' 
      AND mz_sources.type IN ('subsource', 'table')
),

source_errors AS (
    SELECT 'the ' || name || ' source has status ' || status || 
        COALESCE(' with error ' || error || ' ' || details, '') AS description
    FROM mz_internal.mz_source_statuses
    WHERE (status <> 'running' AND type <> 'subsource') 
       OR (status NOT IN ('running', 'starting') AND type = 'subsource')
	   OR (status NOT IN ('running', 'starting') AND type = 'table')
),

context AS (
    SELECT * FROM clusters
	UNION ALL SELECT * FROM sources
	UNION ALL SELECT * FROM subsource_tables
	UNION ALL SELECT * FROM source_errors
)
SELECT string_agg('- ' || description, chr(10)) AS report
FROM context;
