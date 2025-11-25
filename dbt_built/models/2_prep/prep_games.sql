with game_teams as (
    select 
        game_id,
        min(team) as team_1,
        max(team) as team_2
    from {{ ref('clean_game_stats') }}
    group by game_id
)
select 
    g.GAME_ID as game_id,
    cast(g.GAME_DATE as text) as game_day,
    null as game_time,  -- TODO: add if available in source
    gt.team_1 as home_team_id,
    gt.team_2 as away_team_id,
    null as matchup  -- Will be populated in core layer
from {{ ref('clean_games') }} g
left join game_teams gt on g.GAME_ID = gt.game_id


