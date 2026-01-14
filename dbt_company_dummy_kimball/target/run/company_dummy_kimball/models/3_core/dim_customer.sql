
  
    
    

    create  table
      "company_dummy_kimball"."main"."dim_customer__dbt_tmp"
  
    as (
      select 
    cast(customer_id as text) as customer_id,
    customer_name,
    email,
    company_name,
    status,
    cast(lead_id as text) as lead_id,
    created_at
from "company_dummy_kimball"."main"."prep_customer"
    );
  
  