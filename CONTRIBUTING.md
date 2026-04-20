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

### `trellis run` CLI
```bash
trellis run [OPTIONS]

Options:
  --port, -p INTEGER    Port [default: 8089]
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

## Reporting issues
- Use GitHub issues with clear reproduction steps, expected vs. actual behavior, and environment details.

## Communication
- For questions or corporate CLA requests, open an issue or reach out to the maintainers.

