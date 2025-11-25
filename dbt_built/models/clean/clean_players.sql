select * 
from {{ source('nba_source', 'players') }}
