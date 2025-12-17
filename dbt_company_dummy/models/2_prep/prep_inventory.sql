select 
    id as inventory_id,
    product_id,
    current_quantity,
    reorder_level,
    reorder_quantity,
    warehouse_location,
    last_updated
from {{ ref('clean_inventory') }}
