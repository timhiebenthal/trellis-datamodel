select 
    id as team_id,
    full_name as team_name,
    city,
    abbreviation as abbrevation
from {{ ref('clean_teams') }}


