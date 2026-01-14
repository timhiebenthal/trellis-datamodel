
  
  create view "company_dummy_entity"."main"."clean_order_item__dbt_tmp" as (
    select * 
from 'data/order_item.csv'
  );
