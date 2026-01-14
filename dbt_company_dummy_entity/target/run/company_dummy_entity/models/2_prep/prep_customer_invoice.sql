
  
  create view "company_dummy_entity"."main"."prep_customer_invoice__dbt_tmp" as (
    select 
    id as customer_invoice_id,
    order_id,
    invoice_number,
    invoice_date,
    due_date,
    amount,
    status,
    payment_terms,
    paid_date,
    created_at
from "company_dummy_entity"."main"."clean_customer_invoice"
  );
