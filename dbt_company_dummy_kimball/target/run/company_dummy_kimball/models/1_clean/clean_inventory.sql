
  
  create view "company_dummy_kimball"."main"."clean_inventory__dbt_tmp" as (
    select * 
from 'data/inventory.csv'
  );
