select 
    id as player_id,
    full_name,
    null as current_team,  -- TODO: derive from game_stats if needed
    null as draft_year     -- TODO: add if available in source
from {{ ref('clean_players') }}

