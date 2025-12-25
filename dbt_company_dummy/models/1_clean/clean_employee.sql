select * 
from {{ source('mock_csv', 'employee') }}
