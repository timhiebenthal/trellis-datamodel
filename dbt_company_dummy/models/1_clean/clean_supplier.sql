select * 
from {{ source('company_source', 'supplier') }}
