---
name: Create company_dummy project
overview: Create a new `company_dummy/` directory with a simple Python script to generate static mock commercial company data for modeling exercises.
todos: []
---

# Create company_dummy Project

Create a new `company_dummy/` directory with a simple Python script that generates static artificial data for commercial company modeling exercises.

## Structure

The project will have a minimal structure:

- `company_dummy/.gitignore` - Ignore generated data files
- `company_dummy/generate_data.py` - Simple Python script to generate static mock data
- `company_dummy/data/` - Directory for generated CSV files

## Data Model

Generate static mock data for the following tables with referential integrity:

1. **department** (id, name)

- Add: created_at, description (optional)

2. **employee** (id, name, team, supervisor)

- Add: email, department_id (FK to department), hire_date, role, created_at
- Note: "team" might be department_id or a separate field

3. **lead** (id, status, created_at)

- Add: name, email, company_name, source, converted_at (nullable)

4. **customer** (id, created_at, lead_id)

- Add: name, email, company_name, status, lead_id (FK to lead, nullable)

5. **products** (id, name, category)

- Add: price, description, created_at, active (boolean)

6. **order** (id, customer_id, amount, discount)

- Add: order_date, status, employee_id (FK to employee), created_at, updated_at

7. **order_item** (id, order_id, product_id, quantity)

- Add: unit_price, subtotal, created_at

## Implementation Details

### Files to Create

1. **`company_dummy/.gitignore`**

- Ignore `data/*` directory (generated CSV files)

2. **`company_dummy/generate_data.py`** (tracked in git)

- Simple Python script (not marimo notebook)
- Use `faker` library for realistic names, emails, company names
- Use `pandas` to create DataFrames and save as CSV
- Generate small dataset: ~5-10 departments, ~20-30 employees, ~10-15 leads, ~15-20 customers, ~10-15 products, ~30-50 orders, ~50-100 order_items
- Ensure referential integrity (all foreign keys reference valid entities)
- Generate realistic relationships and timestamps
- Save CSV files to `company_dummy/data/` directory
- Should be callable as a function (for CLI integration) or runnable as a script

3. **Update root `.gitignore`**

- Add entry for `company_dummy/data/*`

4. **Add CLI command to `trellis_datamodel/cli.py`**

- Add new command: `trellis generate-company-dummy`
- Command should call the generator script from `company_dummy/generate_data.py`
- Should provide user feedback (e.g., "Generating company dummy data...", "✓ Generated X CSV files")

## Data Generation Approach

- Generate data in dependency order: department → employee → lead → customer → products → order → order_item
- Use realistic distributions and relationships
- Ensure all foreign keys are valid
- Generate timestamps that make sense (e.g., leads created before customers, orders after customers exist)
- Small dataset focused on quality over quantity for modeling exercises

## Notes

- Simple Python script (not marimo notebook)
- Static data generation (no API calls)
- Small dataset (~few dozen orders) perfect for modeling exercises
- Data saved as CSV files in `company_dummy/data/` directory