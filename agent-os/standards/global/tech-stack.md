## Tech stack

This project uses a Python backend with a SvelteKit frontend, designed for Analytics Engineering workflows with dbt-core integration.

### Framework & Runtime
- **Backend Framework:** FastAPI with uvicorn ASGI server
- **CLI Framework:** Typer for command-line interface
- **Language/Runtime:** Python 3.11+ (target audience: Analytics Engineering profiles working with Python and SQL/dbt)
- **Package Manager:** `uv` for Python package and environment management (use `uv sync` for dependencies)
- **Node.js:** Node.js 22+ (or 20.19+) with npm for frontend dependencies

### Frontend
- **JavaScript Framework:** SvelteKit (use unless other frameworks offer significant advantages)
- **CSS Framework:** Tailwind CSS
- **UI Components:** Custom components built with SvelteKit and Tailwind
- **Build Tool:** Vite (via SvelteKit)
- **Visualization:** @xyflow/svelte for graph/flow diagrams, elkjs for layout

### Database & Storage
- **Database:** DuckDB as local default (via dbt-duckdb adapter)
- **Data Modeling:** dbt-core for transformations and schema management
- **Storage:** Store data in dedicated `/data` directory (ask if it should be git-tracked)
- **YAML Handling:** ruamel.yaml for preserving formatting when editing dbt schema files

### Testing & Quality
- **Backend Testing:** pytest with httpx for API testing
- **Frontend Testing:** 
  - Vitest for unit tests
  - Playwright for E2E tests
  - Testing Library for DOM/Svelte component testing
- **Type Checking:** TypeScript for frontend, Python type hints for backend
- **Linting/Formatting:** Follow Python and TypeScript conventions (no specific linters enforced yet)

### Deployment & Infrastructure
- **Hosting:** Google Cloud
- **CI/CD:** GitHub Actions
- **Package Distribution:** Python wheel built with setuptools, frontend bundled as static files

