
  
  create view "company_dummy_entity"."main"."clean_product__dbt_tmp" as (
    select * 
from 'data/products.csv'
  );
