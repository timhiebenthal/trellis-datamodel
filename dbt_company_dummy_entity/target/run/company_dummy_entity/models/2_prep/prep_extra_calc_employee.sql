
  
  create view "company_dummy_entity"."main"."prep_extra_calc_employee__dbt_tmp" as (
    select * from "company_dummy_entity"."main"."prep_employee"
-- just a dummy for lineage testing
-- select * from "company_dummy_entity"."main"."clean_employee" -- just for more lineage
  );
