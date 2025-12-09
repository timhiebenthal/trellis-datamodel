{{ config(version=2) }}

select 
    cast(player_id as text) as player_id,
    full_name,
    cast(current_team as text) as current_team,
    cast(draft_year as text) as draft_year
from {{ ref('prep_players') }}

