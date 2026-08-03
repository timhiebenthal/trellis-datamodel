/* @bruin
name: prep.prep__orders
type: duckdb.sql
connection: test_duckdb
depends:
  - value: raw.raw__orders
    type: asset
materialization:
  type: view
@bruin */
SELECT order_id, customer_id, amount
FROM raw.raw__orders;
