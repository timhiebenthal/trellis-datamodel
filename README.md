# Trellis Data

![Trellis Logo](resources/trellis_with_text.png)

A lightweight, local-first tool to bridge Conceptual Data Modeling, Logical Data Modeling and the Physical Implementation (currently with dbt-core).

## Motivation

**Current workflow pains:**
- ERD diagrams live in separate tools (Lucidchart, draw.io) and quickly become stale or unreadable for large projects
- Data transformations are done isolated from the conceptual data model.
- No single view connecting business concepts to logical schema
- Stakeholders can't easily understand model structure without technical context
- Holistic Data Warehouse Automation Tools exists but do not integrate well with dbt and the Modern Data Stack

**How Trellis helps:**
- Visual data model that stays in sync — reads directly from `manifest.json` / `catalog.json`
- Sketch entities and with their fields and auto-generate schema.yml's for dbt
- Draw relationships on canvas → auto-generates dbt `relationships` tests
- Two views: **Conceptual** (entity names, descriptions) and **Logical** (columns, types, materializations) to jump between high-level architect and execution-view.
- Organize entities based on subdirectories and tags from your pyhsical implementation.
- Write description or tags back to your dbt-project

**Two Ways of getting started** 
- Greenfield: draft entities and fields before writing SQL, then sync to dbt YAML  
- Brownfield: document your existing data model by loading existing dbt models and utilize relationship tests to infer links

## Tutorial & Guide

Check out our [Full Tutorial](https://app.capacities.io/home/667ad256-ca68-4dfd-8231-e77d83127dcf) with video clips showing the core features in action.  Also [General Information](https://app.capacities.io/home/8b7546f6-9028-4209-a383-c4a9ba9be42a) is available.

## Vision

trellis is currently designed and tested specifically for **dbt-core**, but the vision is to be tool-agnostic. As the saying goes: *"tools evolve, concepts don't"* — data modeling concepts persist regardless of the transformation framework you use.

If this project gains traction, we might explore support for:
- **dbt-fusion** through adapter support
- **Pydantic models** as a simple output format
- Other frameworks like [SQLMesh](https://github.com/TobikoData/sqlmesh) or [Bruin](https://github.com/bruin-data/bruin) through adapter patterns, where compatibility allows

This remains a vision for now — the current focus is on making Trellis work well with dbt-core.

## Prerequisites
- **Node.js 22+ (or 20.19+) & npm**  
  - Recommended: Use [nvm](https://github.com/nvm-sh/nvm) to install a compatible version (e.g., `nvm install 22`).
  - Note: System packages (`apt-get`) may be too old for the frontend dependencies.
  - A `.nvmrc` file is included; run `nvm use` to switch to the correct version automatically.
- **Python 3.11+ & [uv](https://github.com/astral-sh/uv)**  
  - Install uv via `curl -LsSf https://astral.sh/uv/install.sh | sh` and ensure it's on your `$PATH`.
- **Make** (optional) for convenience targets defined in the `Makefile`.

## Installation

### Install from PyPI

```bash
pip install trellis-datamodel
# or with uv
uv pip install trellis-datamodel
```

### Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/timhiebenthal/trellis-datamodel.git
cd trellis-datamodel

# Install in editable mode
pip install -e .
# or with uv
uv pip install -e .
```

## Quick Start

1. **Navigate to your dbt project directory**
   ```bash
   cd /path/to/your/dbt-project
   ```

2. **Initialize configuration**
   ```bash
   trellis init
   ```
   This creates a `trellis.yml` file. Edit it to point to your dbt manifest and catalog locations.

3. **Start the server**
   ```bash
   trellis run
   ```

   The server will start on **http://localhost:8089** and automatically open your browser.

## Development Setup

For local development with hot reload:

### Install Dependencies
Run these once per machine (or when dependencies change).

1. **Backend**
   ```bash
   uv sync
   ```
2. **Frontend**
   ```bash
   cd frontend
   npm install
   ```

**Terminal 1 – Backend**
```bash
make backend
# or
uv run trellis run
```
Backend serves the API at http://localhost:8089.

**Terminal 2 – Frontend**
```bash
make frontend
# or
cd frontend && npm run dev
```
Frontend runs at http://localhost:5173 (for development with hot reload).

## Building for Distribution

To build the package with bundled frontend:

```bash
make build-package
```

This will:
1. Build the frontend (`npm run build`)
2. Copy static files to `trellis_datamodel/static/`
3. Build the Python wheel (`uv build`)

The wheel will be in `dist/` and can be installed with `pip install dist/trellis_datamodel-*.whl`.

## CLI Options

```bash
trellis run [OPTIONS]

Options:
  --port, -p INTEGER    Port to run the server on [default: 8089]
  --config, -c TEXT     Path to config file (trellis.yml or config.yml)
  --no-browser          Don't open browser automatically
  --help                Show help message
```

## dbt Metadata
- Generate `manifest.json` and `catalog.json` by running `dbt docs generate` in your dbt project.
- The UI reads these artifacts to power the ERD modeller.
- Without these artifacts, the UI loads but shows no dbt models.

## Configuration

Run `trellis init` to create a starter `trellis.yml` file in your project.

Options:

- `framework`: Transformation framework to use. Currently supported: `dbt-core`. Future: `dbt-fusion`, `sqlmesh`, `bruin`, `pydantic`. Defaults to `dbt-core`.
- `dbt_project_path`: Path to your dbt project directory (relative to `config.yml` or absolute). **Required**.
- `dbt_manifest_path`: Path to `manifest.json` (relative to `dbt_project_path` or absolute). Defaults to `target/manifest.json`.
- `dbt_catalog_path`: Path to `catalog.json` (relative to `dbt_project_path` or absolute). Defaults to `target/catalog.json`.
- `data_model_file`: Path where the data model YAML will be saved (relative to `dbt_project_path` or absolute). Defaults to `data_model.yml`.
- `dbt_model_paths`: List of path patterns to filter which dbt models are shown (e.g., `["3_core"]`). If empty, all models are included.

**Example `trellis.yml`:**
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
make test-e2e       # E2E tests (auto-starts backend with test data)
make test-all       # All tests
```

**Test Data Isolation:**
E2E tests use a separate test data file (`frontend/tests/test_data_model.yml`) to avoid polluting your production data model. **Playwright automatically starts the backend** with the correct environment variable, so you don't need to manage it manually.

```bash
# Just run E2E tests - backend starts automatically with test data
make test-e2e
# OR:
# cd frontend && npm run test:e2e
```

The test data file is automatically cleaned before and after test runs via Playwright's `globalSetup` and `globalTeardown`. Your production `data_model.yml` remains untouched.

### Backend
**Testing Libraries:**
The following testing libraries are defined in `pyproject.toml` under `[project.optional-dependencies]` in the `dev` group:
- [pytest](https://docs.pytest.org/) (Testing framework)
- [httpx](https://www.python-httpx.org/) (Async HTTP client for API testing)

**Installation:**
Unlike `npm`, `uv sync` does not install optional dependencies by default. To include the testing libraries, run:
```bash
uv sync --extra dev
```

**Running Tests:**
```bash
uv run pytest
```

## Collaboration

If you want to collaborate, reach out!

## Contributing and CLA
- Contributions are welcome! Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) for workflow, testing, and PR guidelines.
- All contributors must sign the CLA once per GitHub account. The CLA bot on pull requests will guide you; see [`CLA.md`](CLA.md) for details.

## Acknowledgments
- Thanks to [dbt-colibri](https://github.com/dbt-labs/dbt-colibri) for providing lineage extraction capabilities that enhance trellis's data model visualization features.

## License
- Trellis Datamodel is licensed under the [GNU Affero General Public License v3.0](LICENSE).
- See [`NOTICE`](NOTICE) for a summary of copyright and licensing information.
