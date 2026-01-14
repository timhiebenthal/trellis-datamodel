
  
  create view "company_dummy_entity"."main"."prep_product__dbt_tmp" as (
    select 
    id as product_id,
    name as product_name,
    category,
    price,
    description,
    created_at,
    active
from "company_dummy_entity"."main"."clean_product"
  );
