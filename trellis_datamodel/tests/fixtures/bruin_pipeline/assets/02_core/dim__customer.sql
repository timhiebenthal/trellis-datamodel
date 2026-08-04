/* @bruin
name: core.dim__customer
type: duckdb.sql
connection: test_duckdb
description: One row per customer.
tags:
  - core
  - entity
depends:
  - prep.prep__customers
materialization:
  type: table
  strategy: create+replace
columns:
  - name: customer_id
    type: varchar
    description: Surrogate key for the customer.
    primary_key: true
    checks:
      - name: unique
      - name: not_null
  - name: customer_name
    type: varchar
    description: Display name of the customer.
@bruin */
SELECT customer_id, customer_name
FROM prep.prep__customers;
