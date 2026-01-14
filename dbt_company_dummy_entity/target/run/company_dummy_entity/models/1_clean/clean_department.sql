
  
  create view "company_dummy_entity"."main"."clean_department__dbt_tmp" as (
    select * 
from 'data/department.csv'
  );
