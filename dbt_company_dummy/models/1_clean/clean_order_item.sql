select * 
from {{ source('mock_csv', 'order_item') }}
