/* @bruin
name: core.fct__order
type: duckdb.sql
connection: test_duckdb
description: One row per order line.
tags:
  - core
depends:
  - prep.prep__orders
  - core.dim__customer
materialization:
  type: table
  strategy: merge
columns:
  - name: order_id
    type: varchar
    description: Surrogate key for the order.
    primary_key: true
  - name: customer_id
    type: varchar
    description: Customer that placed the order.
    foreign_key:
      table: core.dim__customer
      column: customer_id
  - name: product_id
    type: varchar
    description: Product that was ordered.
    foreign_key:
      table: dim__product
      column: product_id
  - name: amount
    type: double
    description: Order amount in EUR.
@bruin */
SELECT order_id, customer_id, product_id, amount
FROM prep.prep__orders;
