select * 
from {{ source('nba_source', 'game_stats') }}
