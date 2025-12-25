select * 
from {{ source('mock_csv', 'purchase_order_item') }}
