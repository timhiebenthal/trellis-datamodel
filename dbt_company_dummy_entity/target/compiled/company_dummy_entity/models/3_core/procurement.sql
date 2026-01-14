select 
    cast(poi.purchase_order_item_id as text) as procurement_id,
    cast(poi.purchase_order_id as text) as purchase_order_id,
    cast(poi.product_id as text) as product_id,
    cast(po.supplier_id as text) as supplier_id,
    poi.quantity,
    poi.unit_price,
    poi.subtotal,
    -- Enriched purchase order info
    po.po_number,
    po.po_date,
    po.expected_delivery_date,
    po.status as po_status,
    po.amount as po_amount,
    po.discount as po_discount,
    po.amount - po.discount as po_net_amount,
    po.created_at as po_created_at,
    po.updated_at as po_updated_at,
    -- Procurement-level timestamps
    poi.created_at as procurement_created_at
from "company_dummy_entity"."main"."prep_purchase_order_item" poi
inner join "company_dummy_entity"."main"."prep_purchase_order" po on poi.purchase_order_id = po.purchase_order_id