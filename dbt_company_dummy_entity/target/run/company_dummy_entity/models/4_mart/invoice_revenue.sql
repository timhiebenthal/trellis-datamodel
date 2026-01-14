
  
  create view "company_dummy_entity"."main"."invoice_revenue__dbt_tmp" as (
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
from "company_dummy_entity"."main"."customer_invoice" ci
cross join "company_dummy_entity"."main"."supplier_invoice" si
cross join "company_dummy_entity"."main"."product" p
cross join "company_dummy_entity"."main"."calendar" cal
limit 100
  );
