
  
    
    

    create  table
      "company_dummy_kimball"."main"."dim_customer_invoice__dbt_tmp"
  
    as (
      select 
    cast(customer_invoice_id as text) as customer_invoice_id,
    cast(order_id as text) as order_id,
    invoice_number,
    invoice_date,
    due_date,
    amount,
    status,
    payment_terms,
    paid_date,
    created_at
from "company_dummy_kimball"."main"."prep_customer_invoice"
    );
  
  