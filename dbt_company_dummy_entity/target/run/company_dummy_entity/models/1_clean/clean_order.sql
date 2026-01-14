
  
  create view "company_dummy_entity"."main"."clean_order__dbt_tmp" as (
    select * 
from 'data/order.csv'
  );
