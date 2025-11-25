select distinct
    cast(GAME_DATE as text) as calendar_date,
    cast(strftime(GAME_DATE, '%Y-W%V') as text) as calender_week,
    cast(strftime(GAME_DATE, '%Y-%m') as text) as year_month
from {{ ref('clean_games') }}

