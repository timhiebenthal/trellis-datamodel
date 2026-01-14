
  
  create view "company_dummy_kimball"."main"."clean_supplier_invoice__dbt_tmp" as (
    select * 
from 'data/supplier_invoice.csv'
  );
