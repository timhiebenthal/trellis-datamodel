
  
  create view "company_dummy_kimball"."main"."prep_department__dbt_tmp" as (
    select 
    id as department_id,
    name as department_name,
    description,
    created_at
from "company_dummy_kimball"."main"."clean_department"
  );
