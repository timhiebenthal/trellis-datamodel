# dbt Data Model UI

A local-first tool to bridge Conceptual Data Modeling and Logical dbt Implementation.

## Motivation

**Current dbt workflow pains:**
- ERD diagrams live in separate tools (Lucidchart, draw.io) and quickly become stale
- Data transformations are done isolated from the conceptual data model.
- No single view connecting business concepts to logical schema
- Stakeholders can't easily understand model structure without technical context

**How Trellis helps:**
- Visual data model that stays in sync — reads directly from `manifest.json` / `catalog.json`
- Sketch entities and with their fields and auto-generate schema.yml's for dbt
- Draw relationships on canvas → auto-generates dbt `relationships` tests
- Two views: **Conceptual** (entity names, descriptions) and **Logical** (columns, types, materializations) to jump between high-level architect and execution-view.

**Two Ways of getting started** 
- Greenfield: draft entities and fields before writing SQL, then sync to dbt YAML  
- Brownfield: document your existing data model by loading existing dbt models and utilize relationship tests to infer links

## Prerequisites
- **Node.js 22+ (or 20.19+) & npm**  
  - Recommended: Use [nvm](https://github.com/nvm-sh/nvm) to install a compatible version (e.g., `nvm install 22`).
  - Note: System packages (`apt-get`) may be too old for the frontend dependencies.
  - A `.nvmrc` file is included; run `nvm use` to switch to the correct version automatically.
- **Python 3.12+ & [uv](https://github.com/astral-sh/uv)**  
  - Install uv via `curl -LsSf https://astral.sh/uv/install.sh | sh` and ensure it’s on your `$PATH`.
- **Make** (optional) for convenience targets defined in the `Makefile`.

## Quick Start
The fastest way to get up and running:

```bash
# 1. Install dependencies (first time only)
cd backend && uv sync && cd ../frontend && npm install && cd ..

# 2. Start backend (Terminal 1)
cd backend && uv run python main.py

# 3. Start frontend (Terminal 2 - open a new terminal)
cd frontend && npm run dev
```

Then open **http://localhost:5173** in your browser to preview the application.

## Install Dependencies
Run these once per machine (or when dependencies change).

1. **Backend**
   ```bash
   cd backend
   uv sync
   ```
2. **Frontend**
   ```bash
   cd frontend
   npm install
   ```

## Running (Development)
Run backend and frontend in separate terminals for hot reload.

**Terminal 1 – Backend**
```bash
cd backend
uv run python main.py
```
Backend serves the API at http://localhost:8000.

**Terminal 2 – Frontend**
```bash
cd frontend
npm run dev
```
Frontend runs at http://localhost:5173.

## Running (Production-style)
Build the frontend once, then serve via the backend.

```bash
cd frontend
npm run build

cd ../backend
uv run python main.py
```
The backend hosts the compiled frontend at http://localhost:8000.

## dbt Metadata
- The repo ships with example dbt projects (`dbt_built/`, `dbt_concept/`). Drop `manifest.json` and `catalog.json` into your dbt project's `target/` directory (or point `config.yml` to your dbt project) to power the ERD modeller.
- Without these artifacts, the UI loads but shows no dbt models.

## Configuration
Edit `config.yml` at the project root to configure paths:

- `framework`: Transformation framework to use. Currently supported: `dbt-core`. Future: `dbt-fusion`, `sqlmesh`, `bruin`, `pydantic`. Defaults to `dbt-core`.
- `dbt_project_path`: Path to your dbt project directory (relative to `config.yml` or absolute). **Required**.
- `dbt_manifest_path`: Path to `manifest.json` (relative to `dbt_project_path` or absolute). Defaults to `target/manifest.json`.
- `dbt_catalog_path`: Path to `catalog.json` (relative to `dbt_project_path` or absolute). Defaults to `target/catalog.json`.
- `data_model_file`: Path where the data model YAML will be saved (relative to `dbt_project_path` or absolute). Defaults to `data_model.yml`.
- `dbt_model_paths`: List of path patterns to filter which dbt models are shown (e.g., `["3_core"]`). If empty, all models are included.

**Example `config.yml`:**
```yaml
framework: dbt-core
dbt_project_path: "./dbt_built"
dbt_manifest_path: "target/manifest.json"
dbt_catalog_path: "target/catalog.json"
data_model_file: "data_model.yml"
dbt_model_paths:
  - "3_core"
```


## Testing

### Frontend
**Testing Libraries:**
The following testing libraries are defined in `package.json` under `devDependencies` and are automatically installed when you run `npm install`:
- [Vitest](https://vitest.dev/) (Unit testing)
- [Playwright](https://playwright.dev/) (End-to-End testing)
- [Testing Library](https://testing-library.com/) (DOM & Svelte testing utilities)
- [jsdom](https://github.com/jsdom/jsdom) (DOM environment)

**Running Tests:**
```bash
cd frontend

# Run unit tests
npm run test:unit

# Run E2E tests
npm run test:e2e

# Run all tests
npm run test
```

### Backend
**Testing Libraries:**
The following testing libraries are defined in `pyproject.toml` under `[project.optional-dependencies]` in the `dev` group:
- [pytest](https://docs.pytest.org/) (Testing framework)
- [httpx](https://www.python-httpx.org/) (Async HTTP client for API testing)

**Installation:**
Unlike `npm`, `uv sync` does not install optional dependencies by default. To include the testing libraries, run:
```bash
cd backend
uv sync --extra dev
```

**Running Tests:**
```bash
cd backend
uv run pytest
```
