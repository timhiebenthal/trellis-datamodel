select 
    cast(department_id as text) as department_id,
    department_name,
    description,
    created_at
from "company_dummy_kimball"."main"."prep_department"