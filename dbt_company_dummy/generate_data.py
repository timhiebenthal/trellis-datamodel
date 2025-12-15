"""
Generate mock commercial company data for modeling exercises.

This script generates static CSV files with realistic commercial company data
including departments, employees, leads, customers, products, orders, and order items.
"""

import os
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict

try:
    import pandas as pd
    from faker import Faker
except ImportError as e:
    raise ImportError(
        f"Missing required dependency: {e.name}. "
        "Install with: pip install pandas faker"
    ) from e

# Initialize Faker with seed for reproducible data
fake = Faker()
fake.seed_instance(42)  # For reproducible data
random.seed(42)


def datetime_between_days_ago(start_days_ago: int, end_days_ago: int) -> datetime:
    """Get a faker datetime between (now - start_days_ago) and (now - end_days_ago)."""
    now = datetime.now()
    start = now - timedelta(days=start_days_ago)
    end = now - timedelta(days=end_days_ago)
    return fake.date_time_between_dates(datetime_start=start, datetime_end=end)


def date_between_days_ago(start_days_ago: int, end_days_ago: int) -> date:
    """Get a faker date between (today - start_days_ago) and (today - end_days_ago)."""
    today = date.today()
    start = today - timedelta(days=start_days_ago)
    end = today - timedelta(days=end_days_ago)
    return fake.date_between_dates(date_start=start, date_end=end)


# Project root directory
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def generate_departments(count: int = 8) -> pd.DataFrame:
    """Generate department data."""
    departments = []
    dept_names = [
        "Sales",
        "Marketing",
        "Engineering",
        "Product",
        "Customer Success",
        "Operations",
        "Finance",
        "HR",
    ]

    for i in range(1, count + 1):
        dept_name = dept_names[i - 1] if i <= len(dept_names) else fake.company()
        departments.append(
            {
                "id": i,
                "name": dept_name,
                "created_at": datetime_between_days_ago(730, 365),  # ~2y to ~1y ago
                "description": (
                    fake.text(max_nb_chars=100) if random.random() > 0.3 else None
                ),
            }
        )

    return pd.DataFrame(departments)


def generate_employees(departments: pd.DataFrame, count: int = 25) -> pd.DataFrame:
    """Generate employee data."""
    employees = []
    department_ids = departments["id"].tolist()
    roles = ["Manager", "Senior", "Mid-level", "Junior", "Intern"]

    # First pass: Create all employees without supervisors
    for i in range(1, count + 1):
        dept_id = random.choice(department_ids)
        role = random.choice(roles)

        employee = {
            "id": i,
            "name": fake.name(),
            "email": fake.email(),
            "department_id": dept_id,
            "team": f"Team {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])}",
            "supervisor": None,  # Will be assigned in second pass
            "hire_date": date_between_days_ago(1095, 0),  # ~3y ago to today
            "role": role,
            "created_at": datetime_between_days_ago(1095, 365),  # ~3y to ~1y ago
        }

        employees.append(employee)

    # Second pass: Identify managers and assign supervisors
    manager_ids = [e["id"] for e in employees if e["role"] == "Manager"]

    # Ensure at least one manager exists
    if not manager_ids:
        # Make first employee a manager
        employees[0]["role"] = "Manager"
        manager_ids = [1]

    # Assign supervisors to all employees (including managers)
    for employee in employees:
        # Skip if employee is their own supervisor
        available_managers = [mid for mid in manager_ids if mid != employee["id"]]
        if available_managers:
            employee["supervisor"] = random.choice(available_managers)
        else:
            # Only case: single manager, leave supervisor as None
            employee["supervisor"] = None

    return pd.DataFrame(employees)


def generate_leads(count: int = 12) -> pd.DataFrame:
    """Generate lead data."""
    leads = []
    statuses = ["new", "contacted", "qualified", "converted", "lost"]
    sources = [
        "website",
        "referral",
        "cold_call",
        "email_campaign",
        "social_media",
        "trade_show",
    ]

    for i in range(1, count + 1):
        status = random.choice(statuses)
        converted_at = None
        if status == "converted":
            converted_at = datetime_between_days_ago(180, 0)  # last 6 months

        leads.append(
            {
                "id": i,
                "name": fake.name(),
                "email": fake.email(),
                "company_name": fake.company(),
                "status": status,
                "source": random.choice(sources),
                "created_at": datetime_between_days_ago(365, 0),  # last year
                "converted_at": converted_at,
            }
        )

    return pd.DataFrame(leads)


def generate_customers(leads: pd.DataFrame, count: int = 18) -> pd.DataFrame:
    """Generate customer data."""
    customers = []
    lead_ids = leads["id"].tolist()
    converted_lead_ids = leads[leads["status"] == "converted"]["id"].tolist()
    statuses = ["active", "inactive", "churned"]

    # Some customers come from converted leads
    used_lead_ids = set()

    for i in range(1, count + 1):
        # 60% chance customer came from a lead
        lead_id = None
        if converted_lead_ids and random.random() < 0.6:
            available_leads = [
                lid for lid in converted_lead_ids if lid not in used_lead_ids
            ]
            if available_leads:
                lead_id = random.choice(available_leads)
                used_lead_ids.add(lead_id)

        # If customer came from lead, use lead's info
        if lead_id:
            lead = leads[leads["id"] == lead_id].iloc[0]
            name = lead["name"]
            email = lead["email"]
            company_name = lead["company_name"]
            created_at = lead["converted_at"] or lead["created_at"]
        else:
            name = fake.name()
            email = fake.email()
            company_name = fake.company()
            created_at = datetime_between_days_ago(365, 0)  # last year

        customers.append(
            {
                "id": i,
                "name": name,
                "email": email,
                "company_name": company_name,
                "status": random.choice(statuses),
                "lead_id": lead_id,
                "created_at": created_at,
            }
        )

    return pd.DataFrame(customers)


def generate_products(count: int = 12) -> pd.DataFrame:
    """Generate product data."""
    products = []
    categories = ["Software", "Hardware", "Service", "Consulting", "Subscription"]

    product_names = [
        "Enterprise License",
        "Professional Package",
        "Basic Plan",
        "Premium Support",
        "Custom Integration",
        "Training Program",
        "API Access",
        "Cloud Hosting",
        "On-Premise Solution",
        "Mobile App",
        "Analytics Dashboard",
        "Security Suite",
    ]

    for i in range(1, count + 1):
        name = product_names[i - 1] if i <= len(product_names) else fake.catch_phrase()
        base_price = random.uniform(50, 5000)

        products.append(
            {
                "id": i,
                "name": name,
                "category": random.choice(categories),
                "price": round(base_price, 2),
                "description": (
                    fake.text(max_nb_chars=150) if random.random() > 0.2 else None
                ),
                "created_at": datetime_between_days_ago(730, 180),  # ~2y to ~6m ago
                "active": random.random() > 0.1,  # 90% active
            }
        )

    return pd.DataFrame(products)


def generate_orders(
    customers: pd.DataFrame, employees: pd.DataFrame, count: int = 40
) -> pd.DataFrame:
    """Generate order data."""
    orders = []
    customer_ids = customers["id"].tolist()
    employee_ids = employees["id"].tolist()
    statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]

    for i in range(1, count + 1):
        customer_id = random.choice(customer_ids)
        employee_id = random.choice(employee_ids)
        status = random.choice(statuses)

        # Base amount between 100 and 5000
        amount = random.uniform(100, 5000)
        discount = (
            round(random.uniform(0, 0.3) * amount, 2) if random.random() > 0.6 else 0
        )

        order_date = datetime_between_days_ago(365, 0)  # last year

        orders.append(
            {
                "id": i,
                "customer_id": customer_id,
                "employee_id": employee_id,
                "amount": round(amount, 2),
                "discount": discount,
                "order_date": order_date,
                "status": status,
                "created_at": order_date,
                "updated_at": (
                    order_date + timedelta(days=random.randint(0, 7))
                    if status != "pending"
                    else order_date
                ),
            }
        )

    return pd.DataFrame(orders)


def generate_order_items(
    orders: pd.DataFrame, products: pd.DataFrame, count: int = 80
) -> pd.DataFrame:
    """Generate order item data."""
    order_items = []
    order_ids = orders["id"].tolist()
    product_ids = products[products["active"] == True]["id"].tolist()

    # Create order_items ensuring each order has at least one item
    order_item_map: Dict[int, List[int]] = {}

    for order_id in order_ids:
        order_item_map[order_id] = []

    # Assign items to orders
    for i in range(1, count + 1):
        order_id = random.choice(order_ids)
        product_id = random.choice(product_ids)

        # Get product price
        product = products[products["id"] == product_id].iloc[0]
        unit_price = product["price"]

        # Quantity between 1 and 10
        quantity = random.randint(1, 10)
        subtotal = round(unit_price * quantity, 2)

        order_items.append(
            {
                "id": i,
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "created_at": orders.loc[orders["id"] == order_id, "created_at"].iloc[
                    0
                ],
            }
        )

    return pd.DataFrame(order_items)


def generate_all_data() -> Dict[str, pd.DataFrame]:
    """Generate all data tables in dependency order."""
    print("Generating departments...")
    departments = generate_departments()

    print("Generating employees...")
    employees = generate_employees(departments)

    print("Generating leads...")
    leads = generate_leads()

    print("Generating customers...")
    customers = generate_customers(leads)

    print("Generating products...")
    products = generate_products()

    print("Generating orders...")
    orders = generate_orders(customers, employees)

    print("Generating order items...")
    order_items = generate_order_items(orders, products)

    return {
        "department": departments,
        "employee": employees,
        "lead": leads,
        "customer": customers,
        "products": products,
        "order": orders,
        "order_item": order_items,
    }


def save_dataframes(dataframes: Dict[str, pd.DataFrame]) -> None:
    """Save all dataframes as CSV files."""
    for table_name, df in dataframes.items():
        file_path = DATA_DIR / f"{table_name}.csv"
        df.to_csv(file_path, index=False)
        print(f"  ✓ Saved {len(df)} records to {file_path.name}")


def scaffold_dbt_project():
    """Scaffold dbt project files if they don't exist."""
    dbt_project_file = PROJECT_ROOT / "dbt_project.yml"
    profiles_file = PROJECT_ROOT / "profiles.yml"
    models_dir = PROJECT_ROOT / "models"
    clean_dir = models_dir / "1_clean"
    prep_dir = models_dir / "2_prep"
    core_dir = models_dir / "3_core" / "all"

    # Create directories
    clean_dir.mkdir(parents=True, exist_ok=True)
    prep_dir.mkdir(parents=True, exist_ok=True)
    core_dir.mkdir(parents=True, exist_ok=True)

    # Create dbt_project.yml if it doesn't exist
    if not dbt_project_file.exists():
        dbt_project_content = """name: 'company_dummy'
version: '1.0.0'
config-version: 2

profile: 'company_dummy'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  company_dummy:
    # Configured by layer
    1_clean:
      +materialized: view
    2_prep:
      +materialized: view
    3_core:
      +materialized: table
"""
        dbt_project_file.write_text(dbt_project_content)
        print("  ✓ Created dbt_project.yml")

    # Create profiles.yml if it doesn't exist
    if not profiles_file.exists():
        profiles_content = """company_dummy:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: 'company_dummy.duckdb'
"""
        profiles_file.write_text(profiles_content)
        print("  ✓ Created profiles.yml")

    # Create sources.yml if it doesn't exist
    sources_file = clean_dir / "sources.yml"
    if not sources_file.exists():
        sources_content = """version: 2

sources:
  - name: company_source
    schema: main
    tables:
      - name: department
        description: "Company departments"
        meta:
          external_location: "data/department.csv"
      - name: employee
        description: "Employee records"
        meta:
          external_location: "data/employee.csv"
      - name: lead
        description: "Sales leads"
        meta:
          external_location: "data/lead.csv"
      - name: customer
        description: "Customer records"
        meta:
          external_location: "data/customer.csv"
      - name: products
        description: "Product catalog"
        meta:
          external_location: "data/products.csv"
      - name: order
        description: "Customer orders"
        meta:
          external_location: "data/order.csv"
      - name: order_item
        description: "Order line items"
        meta:
          external_location: "data/order_item.csv"
"""
        sources_file.write_text(sources_content)
        print("  ✓ Created models/1_clean/sources.yml")

    # Create clean models if they don't exist
    clean_models = {
        "clean_customer.sql": """select * 
from {{ source('company_source', 'customer') }}
""",
        "clean_product.sql": """select * 
from {{ source('company_source', 'products') }}
""",
        "clean_lead.sql": """select * 
from {{ source('company_source', 'lead') }}
""",
        "clean_order.sql": """select * 
from {{ source('company_source', 'order') }}
""",
        "clean_order_item.sql": """select * 
from {{ source('company_source', 'order_item') }}
""",
    }

    for filename, content in clean_models.items():
        file_path = clean_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print(f"  ✓ Created models/1_clean/{filename}")

    # Create prep models if they don't exist
    prep_models = {
        "prep_customer.sql": """select 
    id as customer_id,
    name as customer_name,
    email,
    company_name,
    status,
    lead_id,
    created_at
from {{ ref('clean_customer') }}
""",
        "prep_product.sql": """select 
    id as product_id,
    name as product_name,
    category,
    price,
    description,
    created_at,
    active
from {{ ref('clean_product') }}
""",
        "prep_lead.sql": """select 
    id as lead_id,
    name as lead_name,
    email,
    company_name,
    status,
    source,
    created_at,
    converted_at
from {{ ref('clean_lead') }}
""",
        "prep_order.sql": """select 
    id as order_id,
    customer_id,
    employee_id,
    amount,
    discount,
    order_date,
    status,
    created_at,
    updated_at
from {{ ref('clean_order') }}
""",
        "prep_order_item.sql": """select 
    id as order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    subtotal,
    created_at
from {{ ref('clean_order_item') }}
""",
    }

    for filename, content in prep_models.items():
        file_path = prep_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print(f"  ✓ Created models/2_prep/{filename}")

    # Create base entity models if they don't exist
    core_models = {
        "customer.sql": """select 
    cast(customer_id as text) as customer_id,
    customer_name,
    email,
    company_name,
    status,
    cast(lead_id as text) as lead_id,
    created_at
from {{ ref('prep_customer') }}
""",
        "product.sql": """select 
    cast(product_id as text) as product_id,
    product_name,
    category,
    price,
    description,
    created_at,
    active
from {{ ref('prep_product') }}
""",
        "lead.sql": """select 
    cast(lead_id as text) as lead_id,
    lead_name,
    email,
    company_name,
    status,
    source,
    created_at,
    converted_at
from {{ ref('prep_lead') }}
""",
        "purchase.sql": """select 
    cast(oi.order_item_id as text) as purchase_id,
    cast(oi.order_id as text) as order_id,
    cast(oi.product_id as text) as product_id,
    cast(o.customer_id as text) as customer_id,
    oi.quantity,
    oi.unit_price,
    oi.subtotal,
    -- Enriched order info
    o.order_date,
    o.status as order_status,
    o.amount as order_amount,
    o.discount as order_discount,
    o.amount - o.discount as order_net_amount,
    o.created_at as order_created_at,
    o.updated_at as order_updated_at,
    -- Purchase-level timestamps
    oi.created_at as purchase_created_at
from {{ ref('prep_order_item') }} oi
inner join {{ ref('prep_order') }} o on oi.order_id = o.order_id
""",
    }

    for filename, content in core_models.items():
        file_path = core_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print(f"  ✓ Created models/3_core/all/{filename}")

    # Create .yml documentation files for base entities
    core_yml_files = {
        "customer.yml": """version: 2
models:
- name: customer
  description: Customer records
  columns:
  - name: customer_id
    data_type: text
    description: unique customer ID
  - name: customer_name
    data_type: text
    description: customer name
  - name: email
    data_type: text
  - name: company_name
    data_type: text
  - name: status
    data_type: text
  - name: lead_id
    data_type: text
    description: reference to lead if customer came from a lead
    data_tests:
    - relationships:
        arguments:
          to: ref('lead')
          field: lead_id
  - name: created_at
    data_type: timestamp
""",
        "product.yml": """version: 2
models:
- name: product
  description: Product catalog
  columns:
  - name: product_id
    data_type: text
    description: unique product ID
  - name: product_name
    data_type: text
    description: product name
  - name: category
    data_type: text
  - name: price
    data_type: numeric
  - name: description
    data_type: text
  - name: created_at
    data_type: timestamp
  - name: active
    data_type: boolean
""",
        "lead.yml": """version: 2
models:
- name: lead
  description: Sales leads
  columns:
  - name: lead_id
    data_type: text
    description: unique lead ID
  - name: lead_name
    data_type: text
    description: lead contact name
  - name: email
    data_type: text
  - name: company_name
    data_type: text
  - name: status
    data_type: text
  - name: source
    data_type: text
    description: lead source (website, referral, etc.)
  - name: created_at
    data_type: timestamp
  - name: converted_at
    data_type: timestamp
    description: timestamp when lead was converted to customer
""",
        "purchase.yml": """version: 2
models:
- name: purchase
  description: Purchase records at order-item grain with enriched order information
  columns:
  - name: purchase_id
    data_type: text
    description: unique purchase ID (order_item_id)
  - name: order_id
    data_type: text
    description: order ID
  - name: product_id
    data_type: text
    description: product ID
    data_tests:
    - relationships:
        arguments:
          to: ref('product')
          field: product_id
  - name: customer_id
    data_type: text
    description: customer ID
    data_tests:
    - relationships:
        arguments:
          to: ref('customer')
          field: customer_id
  - name: quantity
    data_type: numeric
  - name: unit_price
    data_type: numeric
  - name: subtotal
    data_type: numeric
  - name: order_date
    data_type: timestamp
    description: order date
  - name: order_status
    data_type: text
    description: order status
  - name: order_amount
    data_type: numeric
    description: total order amount
  - name: order_discount
    data_type: numeric
    description: order discount amount
  - name: order_net_amount
    data_type: numeric
    description: net order amount after discount
  - name: order_created_at
    data_type: timestamp
  - name: order_updated_at
    data_type: timestamp
  - name: purchase_created_at
    data_type: timestamp
    description: purchase (order item) creation timestamp
""",
    }

    for filename, content in core_yml_files.items():
        file_path = core_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print(f"  ✓ Created models/3_core/all/{filename}")


def main():
    """Main function to generate and save all data."""
    print("🌿 Generating company dummy data...")
    print()

    dataframes = generate_all_data()

    print()
    print("Saving CSV files...")
    save_dataframes(dataframes)

    print()
    print(f"✓ Successfully generated {len(dataframes)} CSV files in {DATA_DIR}")
    print(f"  Total records: {sum(len(df) for df in dataframes.values())}")

    print()
    print("Scaffolding dbt project...")
    scaffold_dbt_project()
    print()
    print("✓ dbt project ready! Run 'dbt build' to compile and run models.")


if __name__ == "__main__":
    main()
