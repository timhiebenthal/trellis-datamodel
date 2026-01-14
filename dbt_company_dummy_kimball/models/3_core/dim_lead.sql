select 
    cast(lead_id as text) as lead_id,
    lead_name,
    email,
    company_name,
    status,
    source,
    created_at,
    converted_at
from {{ ref('prep_lead') }}
