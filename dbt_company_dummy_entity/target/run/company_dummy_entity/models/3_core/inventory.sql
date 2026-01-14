
  
    
    

    create  table
      "company_dummy_entity"."main"."inventory__dbt_tmp"
  
    as (
      select 
    cast(inventory_id as text) as inventory_id,
    cast(product_id as text) as product_id,
    current_quantity,
    reorder_level,
    reorder_quantity,
    warehouse_location,
    last_updated
from "company_dummy_entity"."main"."prep_inventory"
    );
  
  