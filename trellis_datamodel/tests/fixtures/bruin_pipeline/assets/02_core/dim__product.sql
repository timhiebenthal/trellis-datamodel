/* @bruin
name: core.dim__product
type: duckdb.sql
connection: test_duckdb
description: One row per product.
depends:
  - raw.raw__orders
materialization:
  type: table
columns:
  - name: product_id
    type: varchar
    description: Surrogate key for the product.
    primary_key: true
@bruin */
SELECT DISTINCT product_id
FROM raw.raw__orders;
