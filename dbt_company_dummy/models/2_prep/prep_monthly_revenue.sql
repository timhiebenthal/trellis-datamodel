with orders as (
    select * from {{ ref('prep_order') }}
),

monthly_stats as (
    select
        date_trunc('month', order_date) as order_month,
        count(order_id) as order_count,
        sum(amount) as revenue,
        sum(discount) as total_discount,
        count(distinct customer_id) as active_customers
    from orders
    group by 1
)

select * from monthly_stats
order by order_month desc
