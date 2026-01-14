select * 
from {{ source('mock_csv', 'products') }}
