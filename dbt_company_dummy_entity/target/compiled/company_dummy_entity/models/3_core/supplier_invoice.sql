select 
    cast(si.supplier_invoice_id as text) as supplier_invoice_id,
    cast(si.purchase_order_id as text) as purchase_order_id,
    si.invoice_number,
    si.invoice_date,
    si.due_date,
    si.amount,
    si.status,
    si.payment_terms,
    si.paid_date,
    si.created_at
from "company_dummy_entity"."main"."prep_supplier_invoice" si