# dbt-ontology (ERD Modeller)

A local-first tool to bridge Conceptual Data Modeling and Physical dbt Implementation.

## Prerequisites
- **Node.js 22+ (or 20.19+) & npm**  
  - Recommended: Use [nvm](https://github.com/nvm-sh/nvm) to install a compatible version (e.g., `nvm install 22`).
  - Note: System packages (`apt-get`) may be too old for the frontend dependencies.
  - A `.nvmrc` file is included; run `nvm use` to switch to the correct version automatically.
- **Python 3.10+ & [uv](https://github.com/astral-sh/uv)**  
  - Install uv via `curl -LsSf https://astral.sh/uv/install.sh | sh` and ensure it’s on your `$PATH`.
- **Make** (optional) for convenience targets defined in the `Makefile`.

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
- The repo ships with an empty `dbt/target/` scaffold. Drop `manifest.json` and `catalog.json` there (or point `config.yaml` to a full dbt project) to power the ERD modeller.
- Without these artifacts, the UI loads but shows no dbt models.

## Configuration
- `dbt_manifest_path`: defaults to `../dbt/target/manifest.json` (relative to `backend/`).
- `dbt_catalog_path`: defaults to `../dbt/target/catalog.json` (relative to `backend/`).
- `ontology_file`: saved as `ontology.yaml` in the repo root.

