select 
    id as department_id,
    name as department_name,
    description,
    created_at
from {{ ref('clean_department') }}
