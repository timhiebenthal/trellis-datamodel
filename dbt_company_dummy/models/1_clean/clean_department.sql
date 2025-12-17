select * 
from {{ source('company_source', 'department') }}
