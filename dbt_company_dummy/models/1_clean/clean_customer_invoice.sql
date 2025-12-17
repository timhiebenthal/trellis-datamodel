select * 
from {{ source('company_source', 'customer_invoice') }}
