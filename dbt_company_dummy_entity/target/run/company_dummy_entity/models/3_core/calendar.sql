
  
    
    

    create  table
      "company_dummy_entity"."main"."calendar__dbt_tmp"
  
    as (
      select 
    cast(current_date as text) as calendar_date,
    cast(strftime(current_timestamp, '%Y-W%V') as text) as calendar_week,
    cast(strftime(current_timestamp, '%Y-%m') as text) as year_month
limit 1
    );
  
  