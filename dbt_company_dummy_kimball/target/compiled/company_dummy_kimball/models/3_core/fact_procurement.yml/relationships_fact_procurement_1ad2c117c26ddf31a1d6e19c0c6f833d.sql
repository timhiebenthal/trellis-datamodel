
    
    

with child as (
    select supplier_id as from_field
    from "company_dummy_kimball"."main"."fact_procurement"
    where supplier_id is not null
),

parent as (
    select supplier_id as to_field
    from "company_dummy_kimball"."main"."dim_supplier"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


