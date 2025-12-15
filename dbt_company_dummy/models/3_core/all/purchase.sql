select 
    cast(oi.order_item_id as text) as purchase_id,
    cast(oi.order_id as text) as order_id,
    cast(oi.product_id as text) as product_id,
    cast(o.customer_id as text) as customer_id,
    oi.quantity,
    oi.unit_price,
    oi.subtotal,
    -- Enriched order info
    o.order_date,
    o.status as order_status,
    o.amount as order_amount,
    o.discount as order_discount,
    o.amount - o.discount as order_net_amount,
    o.created_at as order_created_at,
    o.updated_at as order_updated_at,
    -- Purchase-level timestamps
    oi.created_at as purchase_created_at
from {{ ref('prep_order_item') }} oi
inner join {{ ref('prep_order') }} o on oi.order_id = o.order_id
