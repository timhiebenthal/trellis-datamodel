select 
    cast(customer_id as text) as customer_id,
    customer_name,
    email,
    company_name,
    status,
    cast(lead_id as text) as lead_id,
    created_at
from {{ ref('prep_customer') }}