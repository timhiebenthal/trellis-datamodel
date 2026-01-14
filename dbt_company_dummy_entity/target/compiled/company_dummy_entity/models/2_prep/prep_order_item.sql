select 
    id as order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    subtotal,
    created_at
from "company_dummy_entity"."main"."clean_order_item"