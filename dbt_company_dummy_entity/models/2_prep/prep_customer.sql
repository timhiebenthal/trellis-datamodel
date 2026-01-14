select 
    id as customer_id,
    name as customer_name,
    email,
    company_name,
    status,
    lead_id,
    created_at
from {{ ref('clean_customer') }}
