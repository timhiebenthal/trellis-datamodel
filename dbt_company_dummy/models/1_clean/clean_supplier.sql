select * 
from {{ source('mock_csv', 'supplier') }}
