select * 
from {{ source('company_source', 'products') }}
