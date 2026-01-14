select 
    id as product_id,
    name as product_name,
    category,
    price,
    description,
    created_at,
    active
from {{ ref('clean_product') }}
