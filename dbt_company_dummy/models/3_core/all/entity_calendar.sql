select 
    cast(date('now') as text) as calendar_date,
    cast(strftime('%Y-W%V', 'now') as text) as calendar_week,
    cast(strftime('%Y-%m', 'now') as text) as year_month
limit 1

