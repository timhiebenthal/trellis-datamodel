
  
  create view "company_dummy_kimball"."main"."prep_purchase_order__dbt_tmp" as (
    select 
    id as purchase_order_id,
    supplier_id,
    employee_id,
    po_number,
    amount,
    discount,
    po_date,
    expected_delivery_date,
    status,
    created_at,
    updated_at
from "company_dummy_kimball"."main"."clean_purchase_order"
  );
