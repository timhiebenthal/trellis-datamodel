select 
    game_id,
    player as player_id,
    "stats.minutes" as minutes_played,
    "stats.fieldGoalsAttempted" as field_goals_attempted,
    "stats.fieldGoalsMade" as field_goals_made,
    "stats.points" as points,
    "stats.assists" as assists,
    "stats.reboundsTotal" as total_rebounds,
    "stats.reboundsOffensive" as offensive_rebounds,
    "stats.reboundsDefensive" as defensive_rebounds,
    "stats.threePointersAttempted" as "3pt_attempted",
    "stats.threePointersMade" as "3pt_made",
    "stats.freeThrowsAttempted" as free_throws_attempted,
    "stats.freeThrowsMade" as free_throws_made
from {{ ref('clean_game_stats') }}


