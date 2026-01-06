# Repository Guidelines

## Project Structure & Module Organization
- `trellis_datamodel/`: Python backend (Typer CLI + FastAPI), organized into `adapters/`, `routes/`, `services/`, `models/`, and static assets served from `trellis_datamodel/static/`; backend tests live in `trellis_datamodel/tests/`.
- `frontend/`: SvelteKit + TypeScript UI with Tailwind; tests under `frontend/tests/` (Vitest unit, Playwright smoke/E2E).
- `resources/` (branding assets), `scripts/` (utility scripts like version checks), `dbt_built/` and `dbt_company_dummy/` (example dbt artifacts), `dist/` (built wheels), and `trellis.yml` as the default runtime config.

## Build, Test, and Development Commands
- Install deps: `make setup` (runs `uv sync` + `npm install`), or run each command manually if you prefer.
- Run locally: `make backend` (FastAPI on :8089) and `make frontend` (Vite on :5173); `make dev` prints both commands for two terminals. `trellis run -p 8089` starts the bundled app with the packaged static build.
- Package: `make build-package` builds the frontend, copies artifacts to `trellis_datamodel/static/`, and produces wheels in `dist/`.
- Tests: backend `uv run pytest`; frontend `cd frontend && npm run test:smoke|check|test:unit|test:e2e` or `npm run test` for all. Makefile equivalents: `make test-smoke`, `make test-unit`, `make test-e2e`, `make test-all`.

## Coding Style & Naming Conventions
- Python: target 3.11+, 4-space indents, type hints, and small focused functions; keep module and test names `snake_case`. Follow existing FastAPI/Typer patterns for routers and CLI commands.
- Frontend: Svelte components in PascalCase (`Component.svelte`), colocate helpers in the same folder, prefer TypeScript types over `any`, and use Tailwind utility classes consistently. Run `npm run check` before committing to catch TS/Svelte issues.
- Config: `trellis.yml` uses snake_case keys (`dbt_project_path`, `dbt_manifest_path`, etc.); keep secrets and environment-specific paths out of version control.

## Testing Guidelines
- Add or update pytest cases in `trellis_datamodel/tests/test_*.py` alongside the feature you touch; mirror fixtures in `conftest.py` when possible.
- Frontend smoke tests (`npm run test:smoke`) catch crashes; `npm run test:e2e` spins up the backend with isolated test data (`frontend/tests/test_data_model.yml`). Prefer adding Vitest unit coverage for logic and Playwright specs for flows.
- Aim to keep test data deterministic; avoid reusing production `trellis.yml` or dbt artifacts in tests.

## Commit & Pull Request Guidelines
- Commit messages follow short, sentence-style summaries (see `git log`); conventional commit prefixes are not required.
- Create branches from `main`, keep PRs focused, and include context plus linked issues. Run backend pytest and at least `npm run test:smoke` (or `make test-all` for larger changes) before opening a PR.
- Documentation and changelog updates should accompany behavior changes. Signing the CLA (`CLA.md`) is required once; add a DCO sign-off (`git commit -s`) if your organization prefers.
