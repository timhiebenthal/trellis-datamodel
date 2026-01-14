select 
    id as order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    subtotal,
    created_at
from {{ ref('clean_order_item') }}
