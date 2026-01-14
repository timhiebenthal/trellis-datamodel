
  
  create view "company_dummy_entity"."main"."prep_supplier_invoice__dbt_tmp" as (
    select 
    id as supplier_invoice_id,
    purchase_order_id,
    invoice_number,
    invoice_date,
    due_date,
    amount,
    status,
    payment_terms,
    paid_date,
    created_at
from "company_dummy_entity"."main"."clean_supplier_invoice"
  );
