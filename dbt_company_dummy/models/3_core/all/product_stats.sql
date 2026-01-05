select
    cast(product_id as text) as product_id,
    product_name,
    category,
    list_price,
    active,
    total_quantity_sold,
    total_revenue,
    orders_containing_product,
    current_quantity,
    reorder_level,
    needs_reorder,
    case 
        when total_quantity_sold = 0 then 'Dead Stock'
        when total_quantity_sold < 10 then 'Slow Mover'
        when total_quantity_sold > 100 then 'Best Seller'
        else 'Standard'
    end as stock_status
from {{ ref('prep_product_performance') }}
