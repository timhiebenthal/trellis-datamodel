select distinct
    cast(GAME_DATE as text) as calendar_date,
    cast(strftime('%Y-W%V', current_timestamp) as text) as calendar_week,
    cast(strftime('%Y-%M', current_timestamp) as text) as year_month
from {{ ref('clean_games') }}


