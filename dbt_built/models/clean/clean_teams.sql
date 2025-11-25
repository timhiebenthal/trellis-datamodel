select * 
from {{ source('nba_source', 'teams') }}
