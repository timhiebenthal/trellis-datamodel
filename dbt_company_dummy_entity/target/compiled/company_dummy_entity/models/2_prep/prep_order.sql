select 
    id as order_id,
    customer_id,
    employee_id,
    amount,
    discount,
    order_date,
    status,
    created_at,
    updated_at
from "company_dummy_entity"."main"."clean_order"