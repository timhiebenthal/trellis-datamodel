select * 
from {{ source('company_source', 'order_item') }}
