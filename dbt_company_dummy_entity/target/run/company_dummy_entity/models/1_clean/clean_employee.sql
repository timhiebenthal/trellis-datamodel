
  
  create view "company_dummy_entity"."main"."clean_employee__dbt_tmp" as (
    select * 
from 'data/employee.csv'
  );
