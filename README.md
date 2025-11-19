# dbt-ontology (ERD Modeller)

A local-first tool to bridge Conceptual Data Modeling and Physical dbt Implementation.

## Setup

1. **Backend**:
   ```bash
   cd dbt-ontology
   uv sync
   ```
2. **Frontend**:
   ```bash
   cd dbt-ontology/frontend
   npm install
   ```

## Running

### Development Mode (Recommended)
Run frontend and backend separately for hot reload.

**Terminal 1 (Backend):**
```bash
cd dbt-ontology/backend
# or from root: uv run backend/main.py
uv run python main.py
```
API available at http://localhost:8000

**Terminal 2 (Frontend):**
```bash
cd dbt-ontology/frontend
npm run dev
```
UI available at http://localhost:5173

### Production Mode (Single Server)
Build frontend and serve via backend.

```bash
# Build Frontend
cd dbt-ontology/frontend
npm run build

# Run Backend (which serves frontend)
cd ../backend
uv run python main.py
```
Access application at http://localhost:8000

## Configuration
- **Manifest Path**: Defaults to `../../dbt/target/manifest.json` relative to backend.
- **Ontology File**: Saved to `../ontology.yml` relative to backend (root of dbt-ontology).

