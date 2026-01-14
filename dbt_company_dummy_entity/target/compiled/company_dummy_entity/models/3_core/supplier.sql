select 
    cast(supplier_id as text) as supplier_id,
    supplier_name,
    contact_name,
    email,
    phone,
    category,
    status,
    payment_terms,
    created_at
from "company_dummy_entity"."main"."prep_supplier"