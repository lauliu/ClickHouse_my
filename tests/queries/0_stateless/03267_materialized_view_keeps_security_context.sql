DROP TABLE IF EXISTS {CLICKHOUSE_DATABASE:Identifier}.rview;
DROP TABLE IF EXISTS {CLICKHOUSE_DATABASE:Identifier}.wview;

-- Read from view
CREATE MATERIALIZED VIEW rview ENGINE = File(CSV) POPULATE AS SELECT 1 AS c0;
SELECT 1 FROM rview;

-- Write through view populate
CREATE MATERIALIZED VIEW wview ENGINE = Join(ALL, INNER, c0) POPULATE AS SELECT 1 AS c0;
