WITH context AS (
  	SELECT mz_sources.name || ' is a subsource of ' || parent_sources.name AS line
	FROM mz_internal.mz_object_dependencies AS deps
	JOIN mz_catalog.mz_sources AS mz_sources ON mz_sources.id = deps.object_id
	JOIN mz_catalog.mz_sources AS parent_sources ON parent_sources.id = deps.referenced_object_id
	WHERE parent_sources.type <> 'subsource' AND mz_sources.type = 'subsource'

	UNION ALL 

	SELECT s.name || ' is a ' || s.type || ' source on the ' || c.name || ' cluster' AS line 
	FROM mz_sources s INNER JOIN mz_clusters c ON s.cluster_id = c.id WHERE s.id LIKE 'u%' AND type NOT IN ('progress', 'subsource')
  	
	UNION ALL
  
	SELECT name || ' is a ' || size || ' managed cluster with replication factor ' || replication_factor  FROM mz_clusters WHERE id LIKE 'u%'
  
	UNION ALL
  	SELECT 'the ' || name || ' source has status ' || status || ' with error ' || error || ' ' || details
	FROM mz_internal.mz_source_statuses 
	WHERE (status <>'running' AND type <> 'subsource') OR (status NOT IN ('running', 'starting') AND type = 'subsource')
) 

SELECT string_agg(line, '. ') AS report FROM context;
