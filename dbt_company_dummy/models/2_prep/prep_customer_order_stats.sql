with customers as (
    select * from {{ ref('prep_customer') }}
),

orders as (
    select * from {{ ref('prep_order') }}
),

customer_orders as (
    select
        customer_id,
        count(order_id) as total_orders,
        sum(amount) as total_spend,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        avg(amount) as avg_order_value
    from orders
    group by customer_id
),

final as (
    select
        c.customer_id,
        c.customer_name,
        c.status,
        co.total_orders,
        co.total_spend,
        co.first_order_date,
        co.last_order_date,
        co.avg_order_value
    from customers c
    left join customer_orders co using (customer_id)
)

select * from final
