# dbt Company Dummy Data Generator

This directory contains a data generator script that creates realistic mock commercial company data for modeling exercises.

## Overview

The generator creates CSV files with commercial company data including:
- **departments** - Company departments (Sales, Marketing, Engineering, etc.)
- **employees** - Employee records with department assignments and supervisor relationships
- **leads** - Sales leads with status and source tracking
- **customers** - Customer records, some linked to converted leads
- **products** - Product catalog with categories and pricing
- **orders** - Customer orders with employee assignments
- **order_item** - Individual line items for each order

## Prerequisites

The generator requires the following Python packages:
- `pandas` - For data manipulation and CSV export
- `faker` - For generating realistic fake data

### Installing Dependencies

**Option 1: Install with Trellis examples (Recommended)**
```bash
pip install trellis-datamodel[examples]
```

**Option 2: Install dependencies directly**
```bash
pip install pandas faker
```

If you're using the CLI command (`trellis generate-company-data`), installing with `[examples]` ensures all required dependencies are available.

## Usage

### Option 1: Using the Trellis CLI (Recommended)

The easiest way to generate data is using the Trellis CLI command:

```bash
trellis generate-company-data
```

This will:
1. Generate all data tables
2. Save CSV files to `dbt_company_dummy/data/` directory
3. Display progress and summary information

### Option 2: Running the Script Directly

You can also run the generator script directly:

```bash
python dbt_company_dummy/generate_data.py
```

Or from within the `dbt_company_dummy` directory:

```bash
cd dbt_company_dummy
python generate_data.py
```

## Output

All generated CSV files are saved to the `dbt_company_dummy/data/` directory:

- `department.csv` - Department records (~8 records)
- `employee.csv` - Employee records (~25 records)
- `lead.csv` - Lead records (~12 records)
- `customer.csv` - Customer records (~18 records)
- `products.csv` - Product catalog (~12 records)
- `order.csv` - Order records (~40 records)
- `order_item.csv` - Order line items (~80 records)

**Note:** The generated CSV files are ignored by git (see `.gitignore`). Only the generator script is tracked in version control.

## Data Characteristics

### Deterministic Generation
The generator uses fixed seeds (`seed=42`) to ensure reproducible data:
- Same data is generated on every run
- Useful for consistent testing and modeling exercises
- All relationships maintain referential integrity

### Data Relationships
- Employees belong to departments
- Customers can be linked to converted leads
- Orders link customers, employees, and products
- Order items reference orders and products
- Employees have supervisor relationships within departments

### Realistic Data
- Names, emails, and company names use Faker library
- Timestamps follow logical sequences (e.g., leads created before customers)
- Prices, quantities, and amounts use realistic distributions
- Status fields use appropriate business values

## Customization

To modify the generated data, edit `generate_data.py`:

- **Change record counts**: Modify the default `count` parameters in each generator function
- **Adjust data ranges**: Modify price ranges, date ranges, or other numeric values
- **Add fields**: Extend the dictionaries in each generator function
- **Change distributions**: Modify the random selection logic

## Example Use Cases

This dummy data is perfect for:
- Learning dbt modeling patterns
- Testing data transformation logic
- Creating example dbt projects
- Demonstrating ERD relationships
- Practicing SQL queries and joins

## Troubleshooting

### Missing Dependencies
If you see an `ImportError`, install the required packages:
```bash
pip install pandas faker
```

### Permission Errors
Ensure you have write permissions in the `dbt_company_dummy/data/` directory. The script will create the directory if it doesn't exist.

### CLI Command Not Found
If `trellis generate-company-data` doesn't work, ensure:
1. Trellis is installed: `pip install trellis-datamodel`
2. You're in the project root directory
3. The `dbt_company_dummy` directory exists
