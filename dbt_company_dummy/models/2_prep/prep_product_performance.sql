with products as (
    select * from {{ ref('prep_product') }}
),

items as (
    select * from {{ ref('prep_order_item') }}
),

inventory as (
    select * from {{ ref('prep_inventory') }}
),

sales_metrics as (
    select
        product_id,
        count(distinct order_id) as orders_containing_product,
        sum(quantity) as total_quantity_sold,
        sum(subtotal) as total_revenue,
        avg(unit_price) as avg_selling_price
    from items
    group by 1
),

final as (
    select
        p.product_id,
        p.product_name,
        p.category,
        p.price as list_price,
        p.active,
        coalesce(s.orders_containing_product, 0) as orders_containing_product,
        coalesce(s.total_quantity_sold, 0) as total_quantity_sold,
        coalesce(s.total_revenue, 0) as total_revenue,
        i.current_quantity,
        i.reorder_level,
        case 
            when i.current_quantity <= i.reorder_level then true 
            else false 
        end as needs_reorder
    from products p
    left join sales_metrics s using (product_id)
    left join inventory i using (product_id)
)

select * from final
