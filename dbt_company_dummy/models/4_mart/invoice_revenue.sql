-- just a dummy for lineage testing
select 
    ci.customer_invoice_id,
    ci.invoice_number as customer_invoice_number,
    ci.amount as customer_invoice_amount,
    si.supplier_invoice_id,
    si.invoice_number as supplier_invoice_number,
    si.amount as supplier_invoice_amount,
    p.product_id,
    p.product_name,
    cal.calendar_date,
    cal.calendar_week,
    cal.year_month
from {{ ref('entity_customer_invoice') }} ci
cross join {{ ref('entity_supplier_invoice') }} si
cross join {{ ref('entity_product') }} p
cross join {{ ref('entity_calendar') }} cal
limit 100

