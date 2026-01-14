
  
  create view "company_dummy_entity"."main"."clean_customer__dbt_tmp" as (
    select * 
from 'data/customer.csv'
  );
