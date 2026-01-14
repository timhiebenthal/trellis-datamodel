select 
    id as customer_id,
    name as customer_name,
    email,
    company_name,
    status,
    lead_id,
    created_at
from "company_dummy_entity"."main"."clean_customer"