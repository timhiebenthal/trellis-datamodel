# Contributing to trellis Datamodel

Thanks for helping improve trellis Datamodel! This guide explains how to contribute and the expectations for inbound licensing.

## Licensing
- The project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). By contributing, you agree that your contributions are released under AGPL-3.0.
- See `LICENSE` for full terms and `NOTICE` for summary information.

## Contributor License Agreement (CLA)
- All pull requests must be covered by a signed CLA.
- The CLA workflow is automated via GitHub Actions. When you open a PR, a bot will prompt you to sign by adding a comment like:  
  `I have read the CLA Document and I hereby sign the CLA`
- You only need to sign once per GitHub account; the signature is stored in `.github/cla/signatures.json`.
- If you contribute on behalf of a company, ensure you are authorized. If your organization needs a separate corporate CLA, contact the maintainers.

## Developer Certificate of Origin (DCO) (optional but recommended)
- Use `Signed-off-by: Your Name <you@example.com>` in commits (`git commit -s`) to document authorship and intent. This is helpful but not enforced by CI today.

## How to contribute
1. **Fork & branch**: Create a branch from `main`.
2. **Run tests** before submitting (see [Testing](#testing) for the full matrix):
   - Backend: `uv run pytest` (use `uv sync --extra dev` first if dev deps are missing)
   - Frontend: `cd frontend && npm run test:smoke` (or `npm run test` for everything)
3. **Lint/format**: Follow existing project conventions.
4. **PR guidelines**:
   - Keep PRs focused and include context in the description.
   - Update docs and changelog entries when behavior or interfaces change.
   - Ensure CI passes (including the CLA check).

## Development environment

### Prerequisites
- **Node.js 22+ (or 20.19+) & npm** — [nvm](https://github.com/nvm-sh/nvm) recommended; `.nvmrc` is in the repo (`nvm use`). System packages may be too old for frontend deps.
- **Python 3.11+ & [uv](https://github.com/astral-sh/uv)** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- **Make** (optional) — convenience targets in the `Makefile`.

### Clone and install (editable)
```bash
git clone https://github.com/timhiebenthal/trellis-datamodel.git
cd trellis-datamodel
uv pip install -e .
# or: pip install -e .
```

### Run backend and frontend (hot reload)
Install deps once:
```bash
uv sync
cd frontend && npm install
```

**Terminal 1 — backend**
```bash
make backend
# or: uv run trellis run
```
API/UI bundle: **http://localhost:8089**

**Terminal 2 — frontend (dev server)**
```bash
make frontend
# or: cd frontend && npm run dev
```
Vite dev server: **http://localhost:5173**

### Build the Python wheel (bundled frontend)
```bash
make build-package
```
This builds the frontend, copies static assets to `trellis_datamodel/static/`, and runs `uv build`. Install the wheel from `dist/` with `pip install dist/trellis_datamodel-*.whl`.

### Preview a change against another local project

When the trellis checkout and the project you model live on the same machine, this is the default way to preview a change. It runs the wheel you just built inside that project's own environment, so the project keeps its pinned dbt/Bruin tooling, and the published package is never touched.

```bash
# from the trellis checkout, one command
make preview PROJECT=../nba-data            # PORT=8089, CONFIG=trellis.yml by default
```

`make preview` runs the three steps below in order:

```bash
make build-package                          # 1. fresh wheel in dist/
cd ../nba-data                              # 2. into the project
uv pip install --reinstall ~/git_repos/trellis-datamodel/dist/trellis_datamodel-*.whl
uv run --no-sync trellis run -p 8089        # 3. serve it
```

Two flags matter:

- `--reinstall` because a local wheel usually carries the same version as the published beta, so uv would otherwise consider it already satisfied.
- `--no-sync` so `uv run` does not replace the local wheel with the version pinned in the project's lock.

To skip the install entirely, run the wheel from a throwaway environment instead:

```bash
uvx --from ~/git_repos/trellis-datamodel/dist/trellis_datamodel-*.whl \
  trellis run -p 8089 -c ../nba-data/trellis.yml
```

`trellis run` writes entity positions back to the project's data model and canvas layout files the first time it lays out unsaved entities. Preview on a clean checkout, or be ready to `git checkout --` those two files afterwards.

### Debug a change against a live project (hot reload)

`make preview` rebuilds the wheel on every change, which is too slow for debugging. To iterate with a live reload, skip the wheel and point the dev servers at the other project's config.

```bash
# Terminal 1 - this checkout's code, the other project's data
cd ~/git_repos/trellis-datamodel
uv run trellis run -p 8089 -c /path/to/project/trellis.yml --no-browser

# Terminal 2 - Vite dev server, hot reload
cd ~/git_repos/trellis-datamodel/frontend
npm run dev            # open http://localhost:5173
```

Svelte and TypeScript edits reload instantly. Python edits need a restart of terminal 1, because `trellis run` starts uvicorn with `reload=False` (`trellis_datamodel/cli.py`).

This works because:

- Every path in `trellis.yml` resolves relative to the config file's directory, not the working directory (`trellis_datamodel/config.py`), so `-c` can point anywhere.
- The Vite dev server proxies `/api` to `http://localhost:8089`. Override with `VITE_DEV_API_TARGET=http://localhost:9090 npm run dev` when the backend runs on another port.

Two things to keep in mind:

- Terminal 1 uses the checkout's environment, so reconcile and push run whatever dbt or Bruin version this repo has installed, not the project's pins. When that difference matters, install the checkout into the project's environment instead:

  ```bash
  cd /path/to/project
  uv pip install -e ~/git_repos/trellis-datamodel
  uv run --no-sync trellis run -p 8089
  ```

- Port 8089 serves the frontend bundle baked into `trellis_datamodel/static/` by the last `make build-package`, so it can lag behind your working tree. Use 5173 while debugging the frontend, and the write-back caveat above still applies to both ports.

### `trellis run` CLI
```bash
trellis run [OPTIONS]

Options:
  --port, -p INTEGER    Port [default: 8089]
  --host TEXT           Address to bind [default: 127.0.0.1]
  --config, -c TEXT     Path to trellis.yml or config.yml
  --no-browser          Do not open a browser
  --help                Show help
```

## Testing

### Frontend
Libraries (from `package.json`): Vitest, Playwright, Testing Library, jsdom.

> **Playwright system dependencies (Ubuntu / WSL2)**  
> Install native libs before `npm run test:e2e`:
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

```bash
cd frontend

npm run test:smoke   # quick runtime smoke
npm run check        # TypeScript
npm run test:unit    # Vitest
npm run test:e2e     # Playwright (starts backend with test data)
npm run test         # check + smoke + unit + e2e
```

From repo root:
```bash
make test-smoke
make test-check
make test-unit
make test-e2e    # auto-starts backend with test data
make test-all
```

E2E uses `frontend/tests/test_data_model.yml`; Playwright starts the backend with the right env. Production `data_model.yml` is not touched.

### Backend
Dev/test extras are optional:
```bash
uv sync --extra dev
uv run pytest
```

## Backend conventions

### Errors
Services raise the domain exceptions in `trellis_datamodel/exceptions.py`; route handlers do not catch them and do not raise `HTTPException` for domain conditions (unknown id, invalid input, ...). The global handlers in `server.py` map each exception to a status and a JSON body `{"detail": <message>, "error": <code>}`:

| Exception | Status | `error` |
| --- | --- | --- |
| `NotFoundError` | 404 | `not_found` |
| `ValidationError` | 422 | `validation_error` |
| `FeatureDisabledError` | 403 (or the `status_code` it carries) | `feature_disabled` |
| `ConfigurationError` | 400 | `configuration_error` |
| `FileOperationError` | 500 | `file_operation_error` |
| any other `DomainError` | 500 | `domain_error` |
| unhandled exception | 500 | `internal_error` (detail is always `Internal Server Error`) |

Invalid input is 422 everywhere, the same status FastAPI uses for request bodies that fail pydantic validation. Do not map `ValidationError` to 400 in a route.

### Feature flags
Gate a feature with the shared guard in `trellis_datamodel/routes/dependencies.py`, usually on the router:

```python
router = APIRouter(
    prefix="/api",
    dependencies=[Depends(require_feature(lambda: cfg.LINEAGE_ENABLED, "Lineage is disabled. ..."))],
)
```

It raises `FeatureDisabledError` (403). Pass `status_code=404` only where a spec requires a disabled feature to look absent (the metric tree does).

### Request and response models
Pydantic request/response models live in `trellis_datamodel/models/`, not in route modules.

## Reporting issues
- Use GitHub issues with clear reproduction steps, expected vs. actual behavior, and environment details.

## Communication
- For questions or corporate CLA requests, open an issue or reach out to the maintainers.

