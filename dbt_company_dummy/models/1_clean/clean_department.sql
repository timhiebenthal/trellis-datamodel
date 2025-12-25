select * 
from {{ source('mock_csv', 'department') }}
