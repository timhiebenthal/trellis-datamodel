
  
  create view "company_dummy_entity"."main"."clean_lead__dbt_tmp" as (
    select * 
from 'data/lead.csv'
  );
