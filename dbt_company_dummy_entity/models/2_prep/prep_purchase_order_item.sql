select 
    id as purchase_order_item_id,
    purchase_order_id,
    product_id,
    quantity,
    unit_price,
    subtotal,
    created_at
from {{ ref('clean_purchase_order_item') }}
