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

    # Create some managers first for supervisor relationships
    manager_ids = []

    for i in range(1, count + 1):
        dept_id = random.choice(department_ids)
        role = random.choice(roles)
        is_manager = role == "Manager" and random.random() > 0.7

        # Assign supervisor (must be a manager and in same department)
        supervisor_id = None
        if not is_manager and manager_ids:
            potential_supervisors = [
                e["id"]
                for e in employees
                if e["department_id"] == dept_id and e["id"] in manager_ids
            ]
            if potential_supervisors:
                supervisor_id = random.choice(potential_supervisors)

        employee = {
            "id": i,
            "name": fake.name(),
            "email": fake.email(),
            "department_id": dept_id,
            "team": f"Team {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])}",
            "supervisor": supervisor_id,
            "hire_date": date_between_days_ago(1095, 0),  # ~3y ago to today
            "role": role,
            "created_at": datetime_between_days_ago(1095, 365),  # ~3y to ~1y ago
        }

        employees.append(employee)
        if is_manager:
            manager_ids.append(i)

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


if __name__ == "__main__":
    main()
