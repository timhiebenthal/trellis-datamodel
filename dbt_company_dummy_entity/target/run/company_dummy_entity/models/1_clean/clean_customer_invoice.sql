
  
  create view "company_dummy_entity"."main"."clean_customer_invoice__dbt_tmp" as (
    select * 
from 'data/customer_invoice.csv'
  );
