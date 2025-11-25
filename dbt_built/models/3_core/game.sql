with teams as (
    select team_id, abbrevation
    from {{ ref('prep_teams') }}
)
select 
    g.game_id,
    g.game_day,
    g.game_time,
    cast(g.home_team_id as text) as home_team_id,
    cast(g.away_team_id as text) as away_team_id,
    home.abbrevation || ' - ' || away.abbrevation as matchup
from {{ ref('prep_games') }} g
left join teams home on cast(g.home_team_id as text) = home.team_id
left join teams away on cast(g.away_team_id as text) = away.team_id

