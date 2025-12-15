select * 
from {{ source('company_source', 'lead') }}
