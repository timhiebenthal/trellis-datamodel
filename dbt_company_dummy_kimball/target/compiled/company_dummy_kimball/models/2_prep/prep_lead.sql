select 
    id as lead_id,
    name as lead_name,
    email,
    company_name,
    status,
    source,
    created_at,
    converted_at
from "company_dummy_kimball"."main"."clean_lead"