select 
    id as purchase_order_id,
    supplier_id,
    employee_id,
    po_number,
    amount,
    discount,
    po_date,
    expected_delivery_date,
    status,
    created_at,
    updated_at
from {{ ref('clean_purchase_order') }}
