select 
    game_id || '_' || cast(player_id as text) as game_player_id,
    cast(player_id as text) as player_id,
    game_id,
    minutes_played,
    cast(field_goals_attempted as text) as field_goals_attempted,
    cast(field_goals_made as text) as field_goals_made,
    cast(points as text) as points,
    cast(assists as text) as assists,
    cast(total_rebounds as text) as total_rebounds,
    cast(offensive_rebounds as text) as offensive_rebounds,
    cast(defensive_rebounds as text) as defensive_rebounds,
    cast("3pt_attempted" as text) as "3pt_attempted",
    cast("3pt_made" as text) as "3pt_made",
    cast(free_throws_attempted as text) as free_throws_attempted,
    cast(free_throws_made as text) as free_throws_made
from {{ ref('prep_game_stats') }}


