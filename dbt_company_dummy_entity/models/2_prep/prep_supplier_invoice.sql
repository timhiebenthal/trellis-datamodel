select 
    id as supplier_invoice_id,
    purchase_order_id,
    invoice_number,
    invoice_date,
    due_date,
    amount,
    status,
    payment_terms,
    paid_date,
    created_at
from {{ ref('clean_supplier_invoice') }}
