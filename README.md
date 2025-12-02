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

> **Playwright system dependencies (Ubuntu/WSL2)**
>
> The browsers downloaded by Playwright need a handful of native libraries. Install them before running `npm run test:e2e`:
>
> ```bash
> sudo apt-get update && sudo apt-get install -y \
>   libxcursor1 libxdamage1 libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 \
>   libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libasound2 \
>   libnspr4 libnss3 libgbm1 libgles2-mesa libgtk-4-1 libgraphene-1.0-0 \
>   libxslt1.1 libwoff2dec0 libvpx7 libevent-2.1-7 libopus0 \
>   libgstallocators-1.0-0 libgstapp-1.0-0 libgstpbutils-1.0-0 libgstaudio-1.0-0 \
>   libgsttag-1.0-0 libgstvideo-1.0-0 libgstgl-1.0-0 libgstcodecparsers-1.0-0 \
>   libgstfft-1.0-0 libflite1 libflite1-plugins libwebpdemux2 libavif13 \
>   libharfbuzz-icu0 libwebpmux3 libenchant-2-2 libsecret-1-0 libhyphen0 \
>   libwayland-server0 libmanette-0.2-0 libx264-163
> ```

**Running Tests:**

The test suite has multiple levels to catch different types of issues:

```bash
cd frontend

# Quick smoke test (catches 500 errors, runtime crashes, ESM issues)
# Fastest way to verify the app loads without errors
npm run test:smoke

# TypeScript/compilation check
npm run check

# Unit tests
npm run test:unit

# E2E tests (includes smoke test + full test suite)
# Note: Requires backend running with test data (see Test Data Isolation below)
npm run test:e2e

# Run all tests (check + smoke + unit + e2e)
npm run test
```

**Test Levels:**
1. **`npm run check`** - TypeScript compilation errors
2. **`npm run test:smoke`** - Runtime errors (500s, console errors, ESM issues) - **catches app crashes**
3. **`npm run test:unit`** - Unit tests with Vitest
4. **`npm run test:e2e`** - Full E2E tests with Playwright

**Using Makefile:**
```bash
# From project root
make test-smoke     # Quick smoke test
make test-check     # TypeScript check
make test-unit      # Unit tests
make test-backend   # Start backend with test data (Terminal 1)
make test-e2e       # E2E tests (requires test backend in Terminal 1)
make test-all       # All tests
```

**Test Data Isolation:**
E2E tests use a separate test data file (`frontend/tests/test_data_model.yml`) to avoid polluting your production data model. The backend must be started with the `DATAMODEL_DATA_MODEL_PATH` environment variable pointing to the test file:

```bash
# Terminal 1: Start backend with test data
make test-backend
# OR manually:
# DATAMODEL_DATA_MODEL_PATH=$(pwd)/frontend/tests/test_data_model.yml make backend

# Terminal 2: Run tests
make test-e2e
# OR:
# cd frontend && npm run test:e2e
```

The test data file is automatically cleaned before and after test runs. Your production `data_model.yml` remains untouched.

**Note:** If you're running tests, make sure to start the backend with the test data file (`make test-backend`). For normal development, use `make backend` without the env var.

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
