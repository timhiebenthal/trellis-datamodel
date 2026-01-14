
  
    
    

    create  table
      "company_dummy_entity"."main"."lead__dbt_tmp"
  
    as (
      select 
    cast(lead_id as text) as lead_id,
    lead_name,
    email,
    company_name,
    status,
    source,
    created_at,
    converted_at
from "company_dummy_entity"."main"."prep_lead"
    );
  
  