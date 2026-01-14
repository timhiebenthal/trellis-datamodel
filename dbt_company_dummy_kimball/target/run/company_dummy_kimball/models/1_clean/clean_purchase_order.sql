
  
  create view "company_dummy_kimball"."main"."clean_purchase_order__dbt_tmp" as (
    select * 
from 'data/purchase_order.csv'
  );
