# Dual dbt Company Dummy Versions (Kimball & Entity-Logic)

This directory contains two parallel dbt projects that implement different data modeling approaches for the same business domain. This setup enables developers to compare, debug, and demonstrate traditional Kimball dimensional modeling versus entity-logic modeling.

## Overview

Two complete dbt projects are maintained side-by-side:

1. **`dbt_company_dummy_kimball/`** - Traditional Kimball dimensional model
   - Uses `dim_` and `fact_` prefixes for table naming
   - Follows classic star/snowflake schema conventions
   - Data model: `data_model_kimball.yml`

2. **`dbt_company_dummy_entity/`** - Entity-logic model with neutral naming
   - Uses neutral table names without dimension/fact prefixes
   - Focuses on business entity relationships
   - Data model: `data_model_entity.yml`

Both projects share identical base data and transformations, ensuring fair comparison.

## Directory Structure

```
trellis-datamodel/
├── dbt_company_dummy/                 # Original reference project
│   ├── data/                          # Base CSV data files
│   ├── models/
│   │   ├── 1_clean/                  # Data cleaning layer
│   │   ├── 2_prep/                   # Data preparation layer
│   │   ├── 3_core/                   # Core business logic layer
│   │   └── 4_mart/                   # Analytical mart layer
│   └── dbt_project.yml
│
├── dbt_company_dummy_kimball/          # Kimball dimensional model
│   ├── data/                          # Copied from dbt_company_dummy/
│   ├── models/
│   │   ├── 1_clean/                  # Copied from dbt_company_dummy/
│   │   ├── 2_prep/                   # Copied from dbt_company_dummy/
│   │   ├── 3_core/                   # Duplicated with Kimball naming
│   │   │   ├── dim_customer.sql       # Dimensions have dim_ prefix
│   │   │   ├── dim_product.sql
│   │   │   ├── fact_sale.sql         # Facts have fact_ prefix
│   │   │   └── fact_procurement.sql
│   │   └── 4_mart/
│   │       └── invoice_revenue.sql    # References Kimball models
│   ├── exposures_kimball.yml          # Dashboard exposures
│   ├── data_model_kimball.yml         # Entity definitions for trellis
│   └── dbt_project.yml              # name: 'company_dummy_kimball'
│
└── dbt_company_dummy_entity/          # Entity-logic model
    ├── data/                          # Copied from dbt_company_dummy/
    ├── models/
    │   ├── 1_clean/                  # Copied from dbt_company_dummy/
    │   ├── 2_prep/                   # Copied from dbt_company_dummy/
    │   ├── 3_core/                   # Duplicated with neutral naming
    │   │   ├── customer.sql           # No dim_ prefix
    │   │   ├── product.sql
    │   │   ├── sale.sql              # No fact_ prefix
    │   │   └── procurement.sql
    │   └── 4_mart/
    │       └── invoice_revenue.sql    # References entity models
    ├── exposures_entity.yml            # Dashboard exposures
    ├── data_model_entity.yml           # Entity definitions for trellis
    └── dbt_project.yml              # name: 'company_dummy_entity'
```

## Shared Layers

The following layers are shared between both projects:

- **`data/`** - CSV source files (customer.csv, product.csv, etc.)
- **`models/1_clean/`** - Data cleaning transformations
- **`models/2_prep/`** - Data preparation transformations

**Note**: In the current implementation, these are copies rather than symlinks. This means changes to these layers in one project do not automatically propagate to the other. To maintain consistency, apply changes to `dbt_company_dummy/` first, then manually copy to both version projects.

## Naming Convention Differences

### Kimball Version

Uses traditional dimensional modeling prefixes:

| Entity Type | Prefix | Examples |
|------------|---------|----------|
| Dimensions | `dim_` | `dim_customer`, `dim_product`, `dim_calendar` |
| Facts | `fact_` | `fact_sale`, `fact_procurement` |

Key model: `fact_sale` (not `dim_sale`) - represents transactional sales data

### Entity Version

Uses neutral naming without prefixes:

| Entity Type | Examples |
|------------|----------|
| All entities | `customer`, `product`, `calendar` |
| Transactional | `sale`, `procurement` |

Key model: `sale` (not `dim_sale` or `fact_sale`) - neutral representation

### Reference Mappings

| Kimball Reference | Entity Reference |
|-----------------|-----------------|
| `ref('dim_customer')` | `ref('customer')` |
| `ref('fact_sale')` | `ref('sale')` |
| `ref('dim_product')` | `ref('product')` |
| `ref('fact_procurement')` | `ref('procurement')` |

## Switching Between Versions

### Using trellis

1. **Edit `trellis.yml`** configuration:

   For Kimball version:
   ```yaml
   dbt_project_path: "./dbt_company_dummy_kimball"
   data_model_file: "data_model_kimball.yml"
   modeling_style: dimensional_model
   ```

   For Entity version:
   ```yaml
   dbt_project_path: "./dbt_company_dummy_entity"
   data_model_file: "data_model_entity.yml"
   modeling_style: dimensional_model  # or entity_model
   ```

2. **Restart trellis backend**:
   ```bash
   # Stop existing backend (Ctrl+C)
   make backend
   # Or: uv run trellis run -p 8089
   ```

3. **Reload browser** at http://localhost:8089

4. **Verify** the correct models load in the UI

### Using dbt CLI

```bash
# Kimball version
cd dbt_company_dummy_kimball
dbt build          # Build all models
dbt docs generate  # Generate documentation
dbt run --select invoice_revenue  # Run specific model

# Entity version
cd dbt_company_dummy_entity
dbt build
dbt docs generate
dbt run --select invoice_revenue
```

## Testing Steps

### 1. Build Both Projects

```bash
# Build Kimball version
cd dbt_company_dummy_kimball
dbt clean
dbt build
dbt docs generate

# Build Entity version
cd ../dbt_company_dummy_entity
dbt clean
dbt build
dbt docs generate
```

Expected results:
- Both projects build successfully without errors
- Manifest files generated: `target/manifest.json`
- Catalog files generated: `target/catalog.json`

### 2. Verify Mart Consistency

Run the same mart in both versions and compare outputs:

```bash
# Kimball version
cd dbt_company_dummy_kimball
dbt run --select invoice_revenue

# Entity version
cd ../dbt_company_dummy_entity
dbt run --select invoice_revenue
```

Expected results:
- Both marts execute successfully
- Execution times should be similar (~0.1s)
- Outputs should be identical (same base data)

### 3. Test Trellis Loading

```bash
# Load Kimball version
# Edit trellis.yml: dbt_project_path: "./dbt_company_dummy_kimball"
make backend
# Open http://localhost:8089
# Verify: fact_sale displays with blue icon (fact type)
# Verify: dim_customer displays with green icon (dimension type)

# Load Entity version
# Edit trellis.yml: dbt_project_path: "./dbt_company_dummy_entity"
# Restart backend
# Reload browser
# Verify: sale displays with appropriate icon
# Verify: customer displays with appropriate icon
```

Expected results:
- Trellis loads successfully for both versions
- Models display correctly in ERD canvas
- Relationships render properly
- Exposures are visible and reference correct models
- Switching takes less than 1 minute

### 4. Test Switching Workflow

```bash
# Step 1: Load Kimball version
# Edit trellis.yml to point to kimball
make backend
# Verify Kimball models load

# Step 2: Switch to Entity version
# Stop backend (Ctrl+C)
# Edit trellis.yml to point to entity
make backend
# Verify Entity models load

# Step 3: Switch back to Kimball
# Repeat Step 1
```

Expected results:
- No errors during switching
- Clear visual distinction between versions
- UI updates correctly after each switch

## Configuration Files

### dbt_project.yml

Each version has a unique project name:

```yaml
# Kimball version
name: 'company_dummy_kimball'
profile: 'company_dummy_kimball'

# Entity version
name: 'company_dummy_entity'
profile: 'company_dummy_entity'
```

### Data Model Files

Each version has a corresponding data model file for trellis:

- **`data_model_kimball.yml`** - Kimball entity definitions
  - `dbt_model: model.company_dummy_kimball.fact_sale`
  - `entity_type: fact` for transactional models
  - `entity_type: dimension` for descriptive models

- **`data_model_entity.yml`** - Entity-logic definitions
  - `dbt_model: model.company_dummy_entity.sale`
  - Neutral entity types (mostly `dimension`)
  - No dim_/fact_ prefix in model names

### Exposures

Each version has its own exposures file:

- **`exposures_kimball.yml`** - References Kimball models
- **`exposures_entity.yml`** - References entity models

Exposures define BI dashboards and their dependencies on dbt models.

## Development Workflow

### Making Changes to Shared Layers

1. **Edit in `dbt_company_dummy/`** (reference project)
2. **Copy changes to both versions**:
   ```bash
   cp dbt_company_dummy/models/1_clean/clean_customer.sql dbt_company_dummy_kimball/models/1_clean/
   cp dbt_company_dummy/models/1_clean/clean_customer.sql dbt_company_dummy_entity/models/1_clean/
   ```
3. **Rebuild both projects** to verify changes work

### Making Changes to Core Layer

Core layer changes are version-specific:

- **Kimball version**: Edit in `dbt_company_dummy_kimball/models/3_core/`
  - Use `dim_` prefix for dimensions
  - Use `fact_` prefix for facts
  - Update `data_model_kimball.yml` if adding new entities

- **Entity version**: Edit in `dbt_company_dummy_entity/models/3_core/`
  - Use neutral naming
  - Update `data_model_entity.yml` if adding new entities

### Adding New Mart Models

Add mart models to both versions with appropriate references:

```sql
-- Kimball version (dbt_company_dummy_kimball/models/4_mart/)
select
    d.customer_id,
    f.order_date
from {{ ref('dim_customer') }} as d
join {{ ref('fact_sale') }} as f
    on d.customer_id = f.customer_id

-- Entity version (dbt_company_dummy_entity/models/4_mart/)
select
    customer.customer_id,
    sale.order_date
from {{ ref('customer') }} as customer
join {{ ref('sale') }} as sale
    on customer.customer_id = sale.customer_id
```

## Troubleshooting

### Manifest Not Found

If trellis fails to load with "manifest not found" error:

```bash
cd dbt_company_dummy_kimball  # or entity
dbt build
dbt docs generate
# Verify target/manifest.json exists
```

### Model References Not Resolving

If dbt fails with "model not found" error:

1. Check `ref()` calls match actual model names
2. Verify model files exist in correct directory
3. Run `dbt compile` to check for reference errors

### Symlink Issues

If symlinks don't resolve correctly (in WSL or certain filesystems):

```bash
# Check if symlinks exist
ls -la dbt_company_dummy_kimball/models/1_clean

# If copies instead of symlinks, recreate as symlinks:
cd dbt_company_dummy_kimball
rm -rf models/1_clean models/2_prep data
ln -s ../dbt_company_dummy/models/1_clean models/1_clean
ln -s ../dbt_company_dummy/models/2_prep models/2_prep
ln -s ../dbt_company_dummy/data data
```

### Catalog File Missing

If trellis doesn't show column statistics:

```bash
cd dbt_company_dummy_kimball  # or entity
dbt docs generate
# Verify target/catalog.json exists
```

## Performance Considerations

- **Build time**: Both projects build in ~30 seconds
- **Switching time**: < 1 minute to switch versions in trellis
- **Mart execution**: ~0.1s for invoice_revenue mart
- **Memory**: Each project uses separate DuckDB database file
- **Disk space**: ~100MB per project (including target/ directory)

## Comparison Summary

| Aspect | Kimball Version | Entity Version |
|--------|----------------|----------------|
| **Naming** | `dim_`/`fact_` prefixes | Neutral names |
| **Key transaction model** | `fact_sale` | `sale` |
| **entity_type field** | Explicit (fact/dimension) | Mostly neutral |
| **Exposures** | Reference `fact_`/`dim_` models | Reference neutral models |
| **trellis modeling_style** | `dimensional_model` | `dimensional_model` or `entity_model` |
| **Learning curve** | Familiar to data warehouse teams | More intuitive for domain experts |
| **Prefix patterns** | Required for classification | Optional |

## Future Enhancements

Potential improvements to this dual setup:

1. **Automated symlinks**: Create a setup script to manage symlinks
2. **Automated switching**: Helper script to update trellis.yml and rebuild
3. **Shared tests**: Run test suite against both versions simultaneously
4. **Diff visualization**: Show model differences between versions in trellis UI
5. **Side-by-side comparison**: Load both versions in separate browser tabs

## References

- **dbt Core Documentation**: https://docs.getdbt.com/
- **Kimball Methodology**: "The Data Warehouse Toolkit" by Ralph Kimball
- **Trellis Documentation**: See `trellis.yml.example` for configuration options

## Support

For issues or questions:

1. Check this README's troubleshooting section
2. Review `trellis.yml.example` for configuration guidance
3. Examine dbt logs in `dbt_company_dummy_*/logs/dbt.log`
4. Verify manifest and catalog files exist in target directories
