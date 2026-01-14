
  
  create view "company_dummy_kimball"."main"."clean_department__dbt_tmp" as (
    select * 
from 'data/department.csv'
  );
