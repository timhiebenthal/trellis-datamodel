-- DEMO PURPOSE ONLY: This model is a copy of employee.sql with added temporal fields
-- for testing the deduplication strategy for entity relationships feature.
-- It does not contain real historical data.

select 
    cast(employee_id as text) as employee_id,
    employee_name,
    email,
    cast(department_id as text) as department_id,
    team,
    cast(supervisor as text) as supervisor_id,
    hire_date,
    role,
    created_at,
    cast(hire_date as timestamp) as valid_from,
    cast(hire_date as timestamp) + interval '1 year' as valid_to
from {{ ref('prep_employee') }}

