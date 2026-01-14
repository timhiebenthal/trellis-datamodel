
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select lead_id as from_field
    from "company_dummy_entity"."main"."customer"
    where lead_id is not null
),

parent as (
    select lead_id as to_field
    from "company_dummy_entity"."main"."lead"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test