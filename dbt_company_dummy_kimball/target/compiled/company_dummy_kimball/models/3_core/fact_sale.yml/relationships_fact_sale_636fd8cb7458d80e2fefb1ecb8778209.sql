
    
    

with child as (
    select customer_id as from_field
    from "company_dummy_kimball"."main"."fact_sale"
    where customer_id is not null
),

parent as (
    select customer_id as to_field
    from "company_dummy_kimball"."main"."dim_customer"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


