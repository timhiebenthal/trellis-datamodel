select
    cast(null as timestamp) as valid_from,
    cast(null as timestamp) as valid_to,
    player_id,
    full_name,
    current_team as team_id,
from {{ ref('prep_players') }}