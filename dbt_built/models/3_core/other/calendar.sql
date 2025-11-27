select 
    calendar_date,
    calender_week,
    year_month
from {{ ref('prep_calendar') }}

