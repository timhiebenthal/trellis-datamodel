select
    cast(customer_id as text) as customer_id,
    customer_name,
    status,
    total_orders,
    total_spend,
    avg_order_value,
    first_order_date,
    last_order_date,
    current_date - last_order_date as days_since_last_order,
    case 
        when total_spend > 1000 then 'Platinum'
        when total_spend > 500 then 'Gold'
        else 'Silver'
    end as vip_tier
from {{ ref('prep_high_value_customers') }}
