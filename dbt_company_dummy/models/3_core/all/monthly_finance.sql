select
    cast(order_month as date) as report_month,
    revenue,
    total_discount,
    revenue - total_discount as net_revenue,
    active_customers,
    order_count,
    revenue / nullif(order_count, 0) as avg_order_value
from {{ ref('prep_monthly_revenue') }}
