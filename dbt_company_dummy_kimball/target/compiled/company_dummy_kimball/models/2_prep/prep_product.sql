select 
    id as product_id,
    name as product_name,
    category,
    price,
    description,
    created_at,
    active
from "company_dummy_kimball"."main"."clean_product"