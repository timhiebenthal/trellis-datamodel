
  
  create view "company_dummy_kimball"."main"."prep_purchase_order_item__dbt_tmp" as (
    select 
    id as purchase_order_item_id,
    purchase_order_id,
    product_id,
    quantity,
    unit_price,
    subtotal,
    created_at
from "company_dummy_kimball"."main"."clean_purchase_order_item"
  );
