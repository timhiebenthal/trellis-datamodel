
  
  create view "company_dummy_entity"."main"."prep_lead__dbt_tmp" as (
    select 
    id as lead_id,
    name as lead_name,
    email,
    company_name,
    status,
    source,
    created_at,
    converted_at
from "company_dummy_entity"."main"."clean_lead"
  );
