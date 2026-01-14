
  
    
    

    create  table
      "company_dummy_entity"."main"."product__dbt_tmp"
  
    as (
      select 
    cast(product_id as text) as product_id,
    product_name,
    category,
    price,
    description,
    created_at,
    active
from "company_dummy_entity"."main"."prep_product"
    );
  
  