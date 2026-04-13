# Repository Guidelines

## Project Structure
- `trellis_datamodel/`: Python backend (Typer CLI + FastAPI) — adapters/, routes/, services/, models/, static/; tests in `trellis_datamodel/tests/`.
- `frontend/`: SvelteKit + TypeScript + Tailwind; tests in `frontend/tests/` (Vitest unit, Playwright smoke/E2E).
- `resources/`, `scripts/`, `dbt_built/`, `dbt_company_dummy/`, `dist/`, `trellis.yml` (default config).

## Build & Test Commands
- `make setup` — `uv sync` + `npm install`.
- `make backend` — FastAPI :8089. `make frontend` — Vite :5173. `make dev` prints both. `trellis run -p 8089` bundled app.
- `make build-package` — frontend build → `trellis_datamodel/static/` → wheels in `dist/`.
- Backend: `uv run pytest`. Frontend: `cd frontend && npm run test:smoke|check|test:unit|test:e2e|`npm run test` for all. Make equivalents: `make test-smoke|test-unit|test-e2e|test-all`.

## Coding Style
- Python: 3.11+, 4-space indents, type hints, small focused functions. Names `snake_case`. Follow FastAPI/Typer router/CLI patterns.
- Frontend: Svelte components PascalCase (`Component.svelte`), colocate helpers, prefer TS types over `any`, Tailwind consistent. Run `npm run check` before commit.
- Config: `trellis.yml` snake_case keys (`dbt_project_path`, `dbt_manifest_path`, etc.). Keep secrets out of version control.
- **Dimension & Fact**: Green for dimensions (`bg-green-200`, `text-green-900`, `lucide:list`), blue for facts (`bg-blue-200`, `text-blue-900`, `lucide:bar-chart-3`) — canvas, annotations, badges, etc.

## Testing
- pytest cases in `trellis_datamodel/tests/test_*.py` alongside feature; mirror fixtures in `conftest.py` when possible.
- Frontend smoke (`npm run test:smoke`) catches crashes. `npm run test:e2E` spins backend with isolated test data (`frontend/tests/test_data_model.yml`). Prefer Vitest unit + Playwright specs.
- Keep test data deterministic. Avoid production `trellis.yml` or dbt artifacts in tests.

## Commit & PR
- Short sentence summaries (see `git log`). Prefix `(fix:`, `(feat:`, `(style:`, ...).
- Branch from `main`, keep PRs focused, include context + linked issues. Run pytest + `npm run test:smoke` (`make test-all` for larger changes) before opening PR.
- Docs and changelog accompany behavior changes. Sign CLA (`CLA.md`) once. DCO sign-off (`git commit -s`) if org prefers.

## Execution Guidelines
- **Think before coding**: State assumptions. If uncertain, ask. If multiple interpretations exist, present them. Push back on simpler approach.
- **Simplicity first**: No speculative features. No abstractions for single-use. If 200 lines solve what 50 could, rewrite.
- **Surgical changes**: Touch only what needed. Don't "improve" adjacent code. Match existing style. Remove imports/variables your changes make unused.
- **Goal-driven**: Define success criteria. "Fix bug" → write test reproducing it, then make pass. Multi-step: state plan, verify each.