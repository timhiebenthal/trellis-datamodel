
  
  create view "company_dummy_entity"."main"."clean_supplier__dbt_tmp" as (
    select * 
from 'data/supplier.csv'
  );
