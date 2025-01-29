CREATE VIEW materialize_configuration AS
WITH clusters AS (
    SELECT name 
        || ' is a ' || size 
        || ' managed cluster with replication factor ' 
        || replication_factor AS fact
    FROM mz_catalog.mz_clusters
    WHERE id LIKE 'u%' AND managed IS TRUE
),

sources AS (
	SELECT s.name || ' is a ' || s.type || ' source on the ' || c.name || ' cluster' AS fact
	FROM mz_catalog.mz_sources s
	JOIN mz_catalog.mz_clusters c ON s.cluster_id = c.id
	WHERE s.id LIKE 'u%' AND s.type NOT IN ('progress', 'subsource', 'table')
),

subsource_tables AS (
    SELECT 
        mz_sources.name || CASE 
            WHEN mz_sources.type = 'subsource' THEN ' is a subsource of '
            WHEN mz_sources.type = 'table' THEN ' is a table built off '
        END || parent_sources.name AS fact
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
        COALESCE(' with error ' || error || ' ' || details, '') AS fact
    FROM mz_internal.mz_source_statuses
    WHERE (status <> 'running' AND type <> 'subsource') 
       OR (status NOT IN ('running', 'starting') AND type = 'subsource')
	   OR (status NOT IN ('running', 'starting') AND type = 'table')
),

views AS (
    SELECT name || ' is a view'
    FROM mz_views
    WHERE id LIKE 'u%'
),

indexes AS (
    SELECT i.name || ' is an index on ' || o.name || ' on the ' || c.name || ' cluster'
    FROM mz_indexes i 
    JOIN mz_objects o ON i.on_id = o.id 
    JOIN mz_clusters c ON c.id = i.cluster_id
    WHERE i.id LIKE 'u%'
),

context AS (
    SELECT * FROM clusters
	UNION ALL SELECT * FROM sources
	UNION ALL SELECT * FROM subsource_tables
	UNION ALL SELECT * FROM source_errors
    UNION ALL SELECT * FROM views
    UNION ALL SELECT * FROM indexes
)
SELECT string_agg('- ' || fact, chr(10)) AS report
FROM context;
