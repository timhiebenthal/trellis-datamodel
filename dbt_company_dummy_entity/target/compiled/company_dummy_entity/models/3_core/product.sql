select 
    cast(product_id as text) as product_id,
    product_name,
    category,
    price,
    description,
    created_at,
    active
from "company_dummy_entity"."main"."prep_product"