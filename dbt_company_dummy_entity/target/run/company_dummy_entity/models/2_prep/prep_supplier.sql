
  
  create view "company_dummy_entity"."main"."prep_supplier__dbt_tmp" as (
    select 
    id as supplier_id,
    name as supplier_name,
    contact_name,
    email,
    phone,
    category,
    status,
    payment_terms,
    created_at
from "company_dummy_entity"."main"."clean_supplier"
  );
