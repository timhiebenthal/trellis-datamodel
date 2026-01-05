with customer_stats as (
    select * from {{ ref('prep_customer_order_stats') }}
),

high_value as (
    select *
    from customer_stats
    where total_spend > 500
)

select * from high_value
