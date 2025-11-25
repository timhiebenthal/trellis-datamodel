select * 
from {{ source('nba_source', 'games') }}
