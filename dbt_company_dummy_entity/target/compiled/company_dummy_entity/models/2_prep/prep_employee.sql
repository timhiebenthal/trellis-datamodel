select 
    id as employee_id,
    name as employee_name,
    email,
    department_id,
    team,
    supervisor,
    hire_date,
    role,
    created_at
from "company_dummy_entity"."main"."clean_employee"