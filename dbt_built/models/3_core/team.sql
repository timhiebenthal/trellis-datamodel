select 
    cast(team_id as text) as team_id,
    team_name,
    city,
    abbrevation
from {{ ref('prep_teams') }}

