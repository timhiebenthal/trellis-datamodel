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


def generate_suppliers(count: int = 10) -> pd.DataFrame:
    """Generate supplier data."""
    suppliers = []
    categories = [
        "Raw Materials",
        "Components",
        "Finished Goods",
        "Services",
        "Software",
    ]
    statuses = ["active", "inactive", "on_hold"]

    for i in range(1, count + 1):
        suppliers.append(
            {
                "id": i,
                "name": fake.company(),
                "contact_name": fake.name(),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "category": random.choice(categories),
                "status": random.choice(statuses),
                "payment_terms": random.choice(
                    ["Net 30", "Net 60", "Net 15", "COD", "Prepaid"]
                ),
                "created_at": datetime_between_days_ago(730, 180),  # ~2y to ~6m ago
            }
        )

    return pd.DataFrame(suppliers)


def generate_purchase_orders(
    suppliers: pd.DataFrame, employees: pd.DataFrame, count: int = 25
) -> pd.DataFrame:
    """Generate purchase order data."""
    purchase_orders = []
    supplier_ids = suppliers[suppliers["status"] == "active"]["id"].tolist()
    employee_ids = employees["id"].tolist()
    statuses = ["draft", "pending", "approved", "ordered", "received", "cancelled"]

    for i in range(1, count + 1):
        supplier_id = random.choice(supplier_ids) if supplier_ids else None
        employee_id = random.choice(employee_ids)
        status = random.choice(statuses)

        # Base amount between 200 and 8000
        amount = random.uniform(200, 8000)
        discount = (
            round(random.uniform(0, 0.2) * amount, 2) if random.random() > 0.7 else 0
        )

        po_date = datetime_between_days_ago(365, 0)  # last year

        purchase_orders.append(
            {
                "id": i,
                "supplier_id": supplier_id,
                "employee_id": employee_id,
                "po_number": f"PO-{str(i).zfill(6)}",
                "amount": round(amount, 2),
                "discount": discount,
                "po_date": po_date,
                "expected_delivery_date": po_date
                + timedelta(days=random.randint(7, 45)),
                "status": status,
                "created_at": po_date,
                "updated_at": (
                    po_date + timedelta(days=random.randint(0, 14))
                    if status != "draft"
                    else po_date
                ),
            }
        )

    return pd.DataFrame(purchase_orders)


def generate_purchase_order_items(
    purchase_orders: pd.DataFrame, products: pd.DataFrame, count: int = 60
) -> pd.DataFrame:
    """Generate purchase order item data."""
    po_items = []
    po_ids = purchase_orders["id"].tolist()
    product_ids = products["id"].tolist()

    # Create po_items ensuring each PO has at least one item
    po_item_map: Dict[int, List[int]] = {}

    for po_id in po_ids:
        po_item_map[po_id] = []

    # Assign items to purchase orders
    for i in range(1, count + 1):
        po_id = random.choice(po_ids)
        product_id = random.choice(product_ids)

        # Get product price (suppliers might offer different prices)
        product = products[products["id"] == product_id].iloc[0]
        base_price = product["price"]
        # Supplier price might be 60-95% of retail price
        unit_price = round(base_price * random.uniform(0.6, 0.95), 2)

        # Quantity between 5 and 100 (bulk orders)
        quantity = random.randint(5, 100)
        subtotal = round(unit_price * quantity, 2)

        po_items.append(
            {
                "id": i,
                "purchase_order_id": po_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "created_at": purchase_orders.loc[
                    purchase_orders["id"] == po_id, "created_at"
                ].iloc[0],
            }
        )

    return pd.DataFrame(po_items)


def generate_supplier_invoices(
    purchase_orders: pd.DataFrame, count: int = 30
) -> pd.DataFrame:
    """Generate supplier invoice data for purchase orders."""
    supplier_invoices = []
    po_ids = purchase_orders[purchase_orders["status"].isin(["received", "ordered"])][
        "id"
    ].tolist()
    statuses = ["draft", "pending", "approved", "paid", "overdue", "cancelled"]
    payment_terms = ["Net 30", "Net 60", "Net 15", "COD"]

    if len(po_ids) == 0:
        return pd.DataFrame(supplier_invoices)

    used_po_ids = set()

    for i in range(1, min(count + 1, len(po_ids) + 1)):
        # Select a PO that hasn't been invoiced yet
        available_pos = [po_id for po_id in po_ids if po_id not in used_po_ids]
        if not available_pos:
            break

        po_id = random.choice(available_pos)
        used_po_ids.add(po_id)

        po = purchase_orders[purchase_orders["id"] == po_id].iloc[0]

        # Invoice date is typically after PO date
        invoice_date = po["po_date"] + timedelta(days=random.randint(0, 30))
        due_date = invoice_date + timedelta(days=random.choice([15, 30, 45, 60]))

        # Invoice amount matches PO amount (or could be slightly different)
        invoice_amount = po["amount"] - po["discount"]
        # Sometimes there might be additional charges or adjustments
        if random.random() > 0.8:
            invoice_amount = round(invoice_amount * random.uniform(0.95, 1.05), 2)

        status = random.choice(statuses)
        if status == "paid":
            paid_date = invoice_date + timedelta(days=random.randint(0, 60))
        else:
            paid_date = None

        supplier_invoices.append(
            {
                "id": i,
                "purchase_order_id": po_id,
                "invoice_number": f"SUP-INV-{str(i).zfill(6)}",
                "invoice_date": invoice_date,
                "due_date": due_date,
                "amount": invoice_amount,
                "status": status,
                "payment_terms": random.choice(payment_terms),
                "paid_date": paid_date,
                "created_at": invoice_date,
            }
        )

    return pd.DataFrame(supplier_invoices)


def generate_customer_invoices(orders: pd.DataFrame, count: int = 35) -> pd.DataFrame:
    """Generate customer invoice data for orders."""
    customer_invoices = []
    order_ids = orders[orders["status"].isin(["shipped", "delivered", "processing"])][
        "id"
    ].tolist()
    statuses = ["draft", "sent", "paid", "overdue", "cancelled"]
    payment_terms = ["Net 30", "Net 15", "Due on Receipt", "Net 60"]

    if len(order_ids) == 0:
        return pd.DataFrame(customer_invoices)

    used_order_ids = set()

    for i in range(1, min(count + 1, len(order_ids) + 1)):
        # Select an order that hasn't been invoiced yet
        available_orders = [
            order_id for order_id in order_ids if order_id not in used_order_ids
        ]
        if not available_orders:
            break

        order_id = random.choice(available_orders)
        used_order_ids.add(order_id)

        order = orders[orders["id"] == order_id].iloc[0]

        # Invoice date is typically after order date
        invoice_date = order["order_date"] + timedelta(days=random.randint(0, 14))
        due_date = invoice_date + timedelta(days=random.choice([15, 30, 45]))

        # Invoice amount matches order amount
        invoice_amount = order["amount"] - order["discount"]

        status = random.choice(statuses)
        if status == "paid":
            paid_date = invoice_date + timedelta(days=random.randint(0, 45))
        else:
            paid_date = None

        customer_invoices.append(
            {
                "id": i,
                "order_id": order_id,
                "invoice_number": f"CUST-INV-{str(i).zfill(6)}",
                "invoice_date": invoice_date,
                "due_date": due_date,
                "amount": invoice_amount,
                "status": status,
                "payment_terms": random.choice(payment_terms),
                "paid_date": paid_date,
                "created_at": invoice_date,
            }
        )

    return pd.DataFrame(customer_invoices)


def generate_inventory(
    products: pd.DataFrame, purchase_order_items: pd.DataFrame
) -> pd.DataFrame:
    """Generate inventory data based on products and purchase order items."""
    inventory = []
    product_ids = products["id"].tolist()

    for product_id in product_ids:
        # Calculate base inventory from purchase order items
        product_po_items = purchase_order_items[
            purchase_order_items["product_id"] == product_id
        ]
        base_quantity = (
            product_po_items["quantity"].sum() if len(product_po_items) > 0 else 0
        )

        # Add some variance and ensure minimum stock
        current_quantity = max(0, base_quantity + random.randint(-50, 100))
        reorder_level = random.randint(20, 100)
        reorder_quantity = random.randint(50, 200)

        inventory.append(
            {
                "id": product_id,
                "product_id": product_id,
                "current_quantity": current_quantity,
                "reorder_level": reorder_level,
                "reorder_quantity": reorder_quantity,
                "warehouse_location": random.choice(
                    ["Warehouse A", "Warehouse B", "Warehouse C"]
                ),
                "last_updated": datetime_between_days_ago(30, 0),  # last month
            }
        )

    return pd.DataFrame(inventory)


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

    print("Generating customer invoices...")
    customer_invoices = generate_customer_invoices(orders)

    print("Generating suppliers...")
    suppliers = generate_suppliers()

    print("Generating purchase orders...")
    purchase_orders = generate_purchase_orders(suppliers, employees)

    print("Generating purchase order items...")
    purchase_order_items = generate_purchase_order_items(purchase_orders, products)

    print("Generating supplier invoices...")
    supplier_invoices = generate_supplier_invoices(purchase_orders)

    print("Generating inventory...")
    inventory = generate_inventory(products, purchase_order_items)

    return {
        "department": departments,
        "employee": employees,
        "lead": leads,
        "customer": customers,
        "products": products,
        "order": orders,
        "order_item": order_items,
        "customer_invoice": customer_invoices,
        "supplier": suppliers,
        "purchase_order": purchase_orders,
        "purchase_order_item": purchase_order_items,
        "supplier_invoice": supplier_invoices,
        "inventory": inventory,
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
  - name: mock_csv
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
      - name: customer_invoice
        description: "Customer invoices"
        meta:
          external_location: "data/customer_invoice.csv"
      - name: supplier
        description: "Supplier records"
        meta:
          external_location: "data/supplier.csv"
      - name: purchase_order
        description: "Purchase orders to suppliers"
        meta:
          external_location: "data/purchase_order.csv"
      - name: purchase_order_item
        description: "Purchase order line items"
        meta:
          external_location: "data/purchase_order_item.csv"
      - name: supplier_invoice
        description: "Supplier invoices"
        meta:
          external_location: "data/supplier_invoice.csv"
      - name: inventory
        description: "Product inventory levels"
        meta:
          external_location: "data/inventory.csv"
"""
        sources_file.write_text(sources_content)
        print("  ✓ Created models/1_clean/sources.yml")

    # Create clean models if they don't exist
    clean_models = {
        "clean_department.sql": """select * 
from {{ source('mock_csv', 'department') }}
""",
        "clean_employee.sql": """select * 
from {{ source('mock_csv', 'employee') }}
""",
        "clean_customer.sql": """select * 
from {{ source('mock_csv', 'customer') }}
""",
        "clean_product.sql": """select * 
from {{ source('mock_csv', 'products') }}
""",
        "clean_lead.sql": """select * 
from {{ source('mock_csv', 'lead') }}
""",
        "clean_order.sql": """select * 
from {{ source('mock_csv', 'order') }}
""",
        "clean_order_item.sql": """select * 
from {{ source('mock_csv', 'order_item') }}
""",
        "clean_customer_invoice.sql": """select * 
from {{ source('mock_csv', 'customer_invoice') }}
""",
        "clean_supplier.sql": """select * 
from {{ source('mock_csv', 'supplier') }}
""",
        "clean_purchase_order.sql": """select * 
from {{ source('mock_csv', 'purchase_order') }}
""",
        "clean_purchase_order_item.sql": """select * 
from {{ source('mock_csv', 'purchase_order_item') }}
""",
        "clean_supplier_invoice.sql": """select * 
from {{ source('mock_csv', 'supplier_invoice') }}
""",
        "clean_inventory.sql": """select * 
from {{ source('mock_csv', 'inventory') }}
""",
    }

    for filename, content in clean_models.items():
        file_path = clean_dir / filename
        if not file_path.exists():
            file_path.write_text(content)
            print(f"  ✓ Created models/1_clean/{filename}")

    # Create prep models if they don't exist
    prep_models = {
        "prep_department.sql": """select 
    id as department_id,
    name as department_name,
    description,
    created_at
from {{ ref('clean_department') }}
""",
        "prep_employee.sql": """select 
    id as employee_id,
    name as employee_name,
    email,
    department_id,
    team,
    supervisor,
    hire_date,
    role,
    created_at
from {{ ref('clean_employee') }}
""",
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
        "prep_customer_invoice.sql": """select 
    id as customer_invoice_id,
    order_id,
    invoice_number,
    invoice_date,
    due_date,
    amount,
    status,
    payment_terms,
    paid_date,
    created_at
from {{ ref('clean_customer_invoice') }}
""",
        "prep_supplier.sql": """select 
    id as supplier_id,
    name as supplier_name,
    contact_name,
    email,
    phone,
    category,
    status,
    payment_terms,
    created_at
from {{ ref('clean_supplier') }}
""",
        "prep_purchase_order.sql": """select 
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
""",
        "prep_purchase_order_item.sql": """select 
    id as purchase_order_item_id,
    purchase_order_id,
    product_id,
    quantity,
    unit_price,
    subtotal,
    created_at
from {{ ref('clean_purchase_order_item') }}
""",
        "prep_supplier_invoice.sql": """select 
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
""",
        "prep_inventory.sql": """select 
    id as inventory_id,
    product_id,
    current_quantity,
    reorder_level,
    reorder_quantity,
    warehouse_location,
    last_updated
from {{ ref('clean_inventory') }}
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
        "sale.sql": """select 
    cast(oi.order_item_id as text) as sale_id,
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
    -- Sale-level timestamps
    oi.created_at as sale_created_at
from {{ ref('prep_order_item') }} oi
inner join {{ ref('prep_order') }} o on oi.order_id = o.order_id
""",
        "customer_invoice.sql": """select 
    cast(customer_invoice_id as text) as customer_invoice_id,
    cast(order_id as text) as order_id,
    invoice_number,
    invoice_date,
    due_date,
    amount,
    status,
    payment_terms,
    paid_date,
    created_at
from {{ ref('prep_customer_invoice') }}
""",
        "department.sql": """select 
    cast(department_id as text) as department_id,
    department_name,
    description,
    created_at
from {{ ref('prep_department') }}
""",
        "employee.sql": """select 
    cast(employee_id as text) as employee_id,
    employee_name,
    email,
    cast(department_id as text) as department_id,
    team,
    cast(supervisor as text) as supervisor_id,
    hire_date,
    role,
    created_at
from {{ ref('prep_employee') }}
""",
        "supplier.sql": """select 
    cast(supplier_id as text) as supplier_id,
    supplier_name,
    contact_name,
    email,
    phone,
    category,
    status,
    payment_terms,
    created_at
from {{ ref('prep_supplier') }}
""",
        "procurement.sql": """select 
    cast(poi.purchase_order_item_id as text) as procurement_id,
    cast(poi.purchase_order_id as text) as purchase_order_id,
    cast(poi.product_id as text) as product_id,
    cast(po.supplier_id as text) as supplier_id,
    poi.quantity,
    poi.unit_price,
    poi.subtotal,
    -- Enriched purchase order info
    po.po_number,
    po.po_date,
    po.expected_delivery_date,
    po.status as po_status,
    po.amount as po_amount,
    po.discount as po_discount,
    po.amount - po.discount as po_net_amount,
    po.created_at as po_created_at,
    po.updated_at as po_updated_at,
    -- Procurement-level timestamps
    poi.created_at as procurement_created_at
from {{ ref('prep_purchase_order_item') }} poi
inner join {{ ref('prep_purchase_order') }} po on poi.purchase_order_id = po.purchase_order_id
""",
        "supplier_invoice.sql": """select 
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
from {{ ref('prep_supplier_invoice') }} si
""",
        "inventory.sql": """select 
    cast(inventory_id as text) as inventory_id,
    cast(product_id as text) as product_id,
    current_quantity,
    reorder_level,
    reorder_quantity,
    warehouse_location,
    last_updated
from {{ ref('prep_inventory') }}
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
        "sale.yml": """version: 2
models:
- name: sale
  description: Sale records at order-item grain with enriched order information
  columns:
  - name: sale_id
    data_type: text
    description: unique sale ID (order_item_id)
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
  - name: sale_created_at
    data_type: timestamp
    description: sale (order item) creation timestamp
""",
        "customer_invoice.yml": """version: 2
models:
- name: customer_invoice
  description: Customer invoices for sales orders
  columns:
  - name: customer_invoice_id
    data_type: text
    description: unique customer invoice ID
  - name: order_id
    data_type: text
    description: order ID
  - name: invoice_number
    data_type: text
    description: invoice number
  - name: invoice_date
    data_type: timestamp
    description: invoice date
  - name: due_date
    data_type: timestamp
    description: payment due date
  - name: amount
    data_type: numeric
    description: invoice amount
  - name: status
    data_type: text
    description: invoice status (draft, sent, paid, overdue, cancelled)
  - name: payment_terms
    data_type: text
    description: payment terms
  - name: paid_date
    data_type: timestamp
    description: date when invoice was paid
  - name: created_at
    data_type: timestamp
""",
        "department.yml": """version: 2
models:
- name: department
  description: Company departments
  columns:
  - name: department_id
    data_type: text
    description: unique department ID
  - name: department_name
    data_type: text
    description: department name
  - name: description
    data_type: text
  - name: created_at
    data_type: timestamp
""",
        "employee.yml": """version: 2
models:
- name: employee
  description: Employee records
  columns:
  - name: employee_id
    data_type: text
    description: unique employee ID
  - name: employee_name
    data_type: text
    description: employee name
  - name: email
    data_type: text
  - name: department_id
    data_type: text
    description: department ID
    data_tests:
    - relationships:
        arguments:
          to: ref('department')
          field: department_id
  - name: team
    data_type: text
  - name: supervisor_id
    data_type: text
    description: supervisor employee ID
    data_tests:
    - relationships:
        arguments:
          to: ref('employee')
          field: employee_id
  - name: hire_date
    data_type: date
  - name: role
    data_type: text
  - name: created_at
    data_type: timestamp
""",
        "supplier.yml": """version: 2
models:
- name: supplier
  description: Supplier records
  columns:
  - name: supplier_id
    data_type: text
    description: unique supplier ID
  - name: supplier_name
    data_type: text
    description: supplier company name
  - name: contact_name
    data_type: text
  - name: email
    data_type: text
  - name: phone
    data_type: text
  - name: category
    data_type: text
    description: supplier category
  - name: status
    data_type: text
  - name: payment_terms
    data_type: text
  - name: created_at
    data_type: timestamp
""",
        "procurement.yml": """version: 2
models:
- name: procurement
  description: Procurement records at purchase-order-item grain with enriched purchase order information
  columns:
  - name: procurement_id
    data_type: text
    description: unique procurement ID (purchase_order_item_id)
  - name: purchase_order_id
    data_type: text
    description: purchase order ID
  - name: product_id
    data_type: text
    description: product ID
    data_tests:
    - relationships:
        arguments:
          to: ref('product')
          field: product_id
  - name: supplier_id
    data_type: text
    description: supplier ID
    data_tests:
    - relationships:
        arguments:
          to: ref('supplier')
          field: supplier_id
  - name: quantity
    data_type: numeric
  - name: unit_price
    data_type: numeric
  - name: subtotal
    data_type: numeric
  - name: po_number
    data_type: text
    description: purchase order number
  - name: po_date
    data_type: timestamp
    description: purchase order date
  - name: expected_delivery_date
    data_type: timestamp
  - name: po_status
    data_type: text
    description: purchase order status
  - name: po_amount
    data_type: numeric
    description: total purchase order amount
  - name: po_discount
    data_type: numeric
    description: purchase order discount amount
  - name: po_net_amount
    data_type: numeric
    description: net purchase order amount after discount
  - name: po_created_at
    data_type: timestamp
  - name: po_updated_at
    data_type: timestamp
  - name: procurement_created_at
    data_type: timestamp
    description: procurement (purchase order item) creation timestamp
""",
        "supplier_invoice.yml": """version: 2
models:
- name: supplier_invoice
  description: Supplier invoices for purchase orders
  columns:
  - name: supplier_invoice_id
    data_type: text
    description: unique supplier invoice ID
  - name: purchase_order_id
    data_type: text
    description: purchase order ID
  - name: invoice_number
    data_type: text
    description: supplier invoice number
  - name: invoice_date
    data_type: timestamp
    description: invoice date
  - name: due_date
    data_type: timestamp
    description: payment due date
  - name: amount
    data_type: numeric
    description: invoice amount
  - name: status
    data_type: text
    description: invoice status (draft, pending, approved, paid, overdue, cancelled)
  - name: payment_terms
    data_type: text
    description: payment terms
  - name: paid_date
    data_type: timestamp
    description: date when invoice was paid
  - name: created_at
    data_type: timestamp
""",
        "inventory.yml": """version: 2
models:
- name: inventory
  description: Product inventory levels
  columns:
  - name: inventory_id
    data_type: text
    description: unique inventory ID (product_id)
  - name: product_id
    data_type: text
    description: product ID
    data_tests:
    - relationships:
        arguments:
          to: ref('product')
          field: product_id
  - name: current_quantity
    data_type: numeric
    description: current stock quantity
  - name: reorder_level
    data_type: numeric
    description: reorder threshold
  - name: reorder_quantity
    data_type: numeric
    description: quantity to reorder
  - name: warehouse_location
    data_type: text
  - name: last_updated
    data_type: timestamp
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
