/* @bruin
name: prep.prep__page_views
type: duckdb.sql
connection: test_duckdb
depends:
  - raw.raw__page_views
materialization:
  type: view
@bruin */
SELECT page_view_id, customer_id
FROM raw.raw__page_views;
