select * 
from {{ source('mock_csv', 'lead') }}
