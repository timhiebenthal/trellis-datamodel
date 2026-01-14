
  
    
    

    create  table
      "company_dummy_kimball"."main"."dim_employee__dbt_tmp"
  
    as (
      select 
    cast(employee_id as text) as employee_id,
    employee_name,
    email,
    cast(department_id as text) as department_id,
    team,
    cast(supervisor as text) as supervisor_id,
    hire_date,
    role,
    created_at
from "company_dummy_kimball"."main"."prep_employee"
    );
  
  