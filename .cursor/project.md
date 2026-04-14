# Trellis Data Model - Project Overview

## Mission & Vision

### Vision Statement

Trellis = lightweight, local-first tool bridging Conceptual, Logical, Physical data modeling. Empowers Analytics Engineers + Data Teams: visual data models synced w/ transformation code. Eliminates disconnect between biz concepts + technical impl.

### Core Problem We Solve

**The Data Modeling Gap:**
- ERD diagrams in separate tools (Lucidchart, draw.io) → stale/unreadable at scale
- Transformations isolated from conceptual data model
- No single view: biz concepts → logical schema
- Stakeholders can't understand model structure w/o technical context
- Holistic DWH Automation Tools exist but don't integrate w/ dbt/Modern Data Stack

### Our Solution

Trellis: **visual data model editor** that:
- **Stays in sync** — reads directly from dbt `manifest.json` / `catalog.json`
- **Bidirectional workflow** — sketch entities+fields → auto-generate `schema.yml`; OR load existing dbt models → visualize+document
- **Relationship mapping** — draw relationships on canvas → auto-generates dbt `relationships` tests
- **Dual views** — toggle between **Conceptual** (entity names, descriptions) and **Logical** (columns, types, materializations)
- **Organization** — organize entities by subdirs + tags from physical impl
- **Round-trip editing** — write descriptions+tags back to dbt project

### Target Users

**Primary Personas:**
1. **Analytics Engineers** - Daily dbt-core users, need to visualize+document data models
2. **Data Engineers** - Design+maintain complex DWH schemas
3. **Data Modelers** - Bridge biz requirements + technical impl

**Secondary Personas:**
4. **Data Stakeholders** - Need model understanding w/o deep technical knowledge

### Core Values

1. **Local-First**: Data stays on your machine. No cloud deps, no vendor lock-in.
2. **Tool-Agnostic Vision**: Currently dbt-core focused; "tools evolve, concepts don't" — modeling concepts persist across frameworks.
3. **Developer Experience**: Seamless dbt workflow integration. No process disruption.
4. **Visual Clarity**: Complex models → intuitive visual repr.
5. **Bidirectional Sync**: Changes flow both ways — code↔visualization.

### Differentiation

Trellis unique:
- **Only tool** w/ true bidirectional sync w/ dbt-core
- **Local-first** — no cloud account, complete privacy
- **Lightweight** — fast, no heavy infra
- **Visual-first** — for visual thinkers
- **Modern Stack** — modern web tech, not legacy desktop

## Technical Stack

### Architecture

**High-Level Architecture:**
- **Backend**: FastAPI REST API serving data model ops + dbt integration
- **Frontend**: SvelteKit SPA for visual data modeling
- **Storage**: YAML files (`data_model.yml`, `canvas_layout.yml`) in dbt project dir
- **Deployment**: Python package w/ bundled frontend static files

**Communication:**
- REST API: frontend ↔ backend
- Backend reads/writes dbt artifacts (`manifest.json`, `catalog.json`)
- Backend reads/writes YAML config files

### Backend Stack

**Core Framework:**
- **Language**: Python 3.11+
- **Web Framework**: FastAPI 0.121.3+
- **ASGI Server**: Uvicorn 0.38.0+
- **CLI Framework**: Typer 0.9.0+

**Package Management:**
- **Package Manager**: `uv` (Astral's uv) for Python dep + env mgmt
- **Installation**: `uv sync` for dev, `uv pip install` for dist

**Data Processing:**
- **dbt Integration**: dbt-core 1.10.5+ (<2.0)
- **dbt Adapter**: dbt-duckdb 1.10.0+ (example/test projects)
- **YAML Handling**:
  - `pyyaml` 6.0.3+ for standard YAML ops (data model files)
  - `ruamel.yaml` 0.18.0+ for dbt schema.yml editing (preserves formatting)

**Configuration:**
- **Config Management**: Custom YAML-based config (`trellis.yml`)
- **Environment Variables**: `python-dotenv` 1.2.1+ for secrets mgmt

**Testing:**
- **Test Framework**: pytest 8.0.0+
- **HTTP Testing**: httpx 0.27.0+ for async API testing
- **Test Structure**: Tests in `trellis_datamodel/tests/`

### Frontend Stack

**Core Framework:**
- **Language**: TypeScript
- **Framework**: SvelteKit (latest stable)
- **Build Tool**: Vite (via SvelteKit)

**Styling:**
- **CSS Framework**: Tailwind CSS
- **Component Library**: Custom Svelte components w/ Tailwind
- **Responsive Design**: Mobile-first w/ Tailwind breakpoints

**Visualization:**
- **Graph/Flow Library**: @xyflow/svelte for interactive node-based diagrams
- **Layout Engine**: elkjs for auto graph layout algorithms

**Testing:**
- **Unit Testing**: Vitest
- **E2E Testing**: Playwright
- **Component Testing**: Testing Library (Svelte)
- **DOM Environment**: jsdom for unit tests

**Package Management:**
- **Package Manager**: npm
- **Node Version**: Node.js 22+ (or 20.19+)
- **Version Management**: `.nvmrc` for nvm compat

### Database & Storage

**Data Storage:**
- **Primary Storage**: YAML files in dbt project dir
  - `data_model.yml`: Entity + relationship definitions
  - `canvas_layout.yml`: Visual layout/positioning data
- **dbt Artifacts**: Read-only access to dbt-generated files
  - `manifest.json`: dbt project structure + deps
  - `catalog.json`: Column metadata + types

**Database (Example/Testing):**
- **Default**: DuckDB (via dbt-duckdb adapter)
- **Purpose**: Example projects + testing; not required for core

### Development Tools

**Version Control:**
- **VCS**: Git
- **Hosting**: GitHub
- **CI/CD**: GitHub Actions

**Code Quality:**
- **Type Checking**: 
  - TypeScript for frontend (`npm run check`)
  - Python type hints for backend
- **Linting/Formatting**: Follow lang conventions (no enforced linters yet)

**Build & Distribution:**
- **Python Build**: setuptools + wheel
- **Frontend Build**: Vite prod build (`npm run build`)
- **Package Distribution**: Python wheel w/ bundled frontend static files
- **Distribution Channel**: PyPI

### Development Environment

**Prerequisites:**
- **Python**: 3.11+ w/ `uv` installed
- **Node.js**: 22+ (or 20.19+) w/ npm
- **Make**: Optional, for Makefile convenience targets

**Development Setup:**
- **Backend Dev**: `make backend` or `uv run trellis run` (hot reload)
- **Frontend Dev**: `make frontend` or `cd frontend && npm run dev` (hot reload)
- **Devcontainer**: Supported for WSL/Windows collab

**Build Process:**
- **Frontend Build**: `npm run build` in `frontend/` dir
- **Package Build**: `make build-package` (builds frontend + Python wheel)
- **Output**: Python wheel in `dist/` dir

### Technology Decisions & Rationale

**Why FastAPI?**
- Modern, fast Python web framework
- Auto OpenAPI docs
- Async support for I/O-bound ops
- Type hints support

**Why SvelteKit?**
- Lightweight + performant
- Great DX
- Built-in routing + SSR
- Strong TypeScript support

**Why Tailwind CSS?**
- Rapid UI dev
- Consistent design system
- Small bundle w/ purging
- Excellent docs

**Why @xyflow/svelte?**
- Industry-standard graph viz library
- Svelte-specific bindings
- Interactive node/edge manipulation
- Extensible + customizable

**Why YAML for Storage?**
- Human-readable
- Easy to version control
- Familiar to dbt users
- No DB setup required (local-first)

**Why uv for Python?**
- Fast dep resolution
- Modern Python pkg mgmt
- Better than pip for dev workflows
- Compatible w/ standard Python packaging

### Standards & Conventions

See `agent-os/standards/` for detailed coding standards:
- Backend: API design, models, migrations, queries
- Frontend: Components, CSS, accessibility, responsive design
- Global: Coding style, commenting, error handling, validation, testing