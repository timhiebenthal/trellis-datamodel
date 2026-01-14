
  
  create view "company_dummy_entity"."main"."clean_purchase_order_item__dbt_tmp" as (
    select * 
from 'data/purchase_order_item.csv'
  );
