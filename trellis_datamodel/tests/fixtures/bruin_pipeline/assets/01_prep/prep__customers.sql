/* @bruin
name: prep.prep__customers
type: duckdb.sql
connection: test_duckdb
depends:
  - raw.raw__customers
materialization:
  type: view
@bruin */
SELECT customer_id, customer_name
FROM raw.raw__customers;
