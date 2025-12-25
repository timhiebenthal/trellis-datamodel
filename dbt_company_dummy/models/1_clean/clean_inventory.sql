select * 
from {{ source('mock_csv', 'inventory') }}
