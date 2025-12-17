select * 
from {{ source('company_source', 'purchase_order') }}
