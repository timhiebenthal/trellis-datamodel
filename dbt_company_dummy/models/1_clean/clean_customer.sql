select * 
from {{ source('mock_csv', 'customer') }}
