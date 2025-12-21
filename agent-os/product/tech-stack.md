# Trellis Data Model - Technical Stack

## Overview

Trellis is built as a modern, local-first application with a Python backend and SvelteKit frontend, designed specifically for Analytics Engineering workflows with dbt-core integration.

## Architecture

### High-Level Architecture
- **Backend**: FastAPI REST API serving data model operations and dbt integration
- **Frontend**: SvelteKit SPA providing visual data modeling interface
- **Storage**: YAML files (`data_model.yml`, `canvas_layout.yml`) stored in dbt project directory
- **Deployment**: Python package with bundled frontend static files

### Communication
- REST API between frontend and backend
- Backend reads/writes dbt artifacts (`manifest.json`, `catalog.json`)
- Backend reads/writes YAML configuration files

## Backend Stack

### Core Framework
- **Language**: Python 3.11+
- **Web Framework**: FastAPI 0.121.3+
- **ASGI Server**: Uvicorn 0.38.0+
- **CLI Framework**: Typer 0.9.0+

### Package Management
- **Package Manager**: `uv` (Astral's uv) for Python dependency and environment management
- **Installation**: `uv sync` for development, `uv pip install` for distribution

### Data Processing
- **dbt Integration**: dbt-core 1.10.5+ (<2.0)
- **dbt Adapter**: dbt-duckdb 1.10.0+ (for example/test projects)
- **YAML Handling**:
  - `pyyaml` 6.0.3+ for standard YAML operations (data model files)
  - `ruamel.yaml` 0.18.0+ for dbt schema.yml editing (preserves formatting)

### Configuration
- **Config Management**: Custom YAML-based config (`trellis.yml`)
- **Environment Variables**: `python-dotenv` 1.2.1+ for secrets management

### Testing
- **Test Framework**: pytest 8.0.0+
- **HTTP Testing**: httpx 0.27.0+ for async API testing
- **Test Structure**: Tests in `trellis_datamodel/tests/`

## Frontend Stack

### Core Framework
- **Language**: TypeScript
- **Framework**: SvelteKit (latest stable)
- **Build Tool**: Vite (via SvelteKit)

### Styling
- **CSS Framework**: Tailwind CSS
- **Component Library**: Custom Svelte components built with Tailwind
- **Responsive Design**: Mobile-first approach with Tailwind breakpoints

### Visualization
- **Graph/Flow Library**: @xyflow/svelte for interactive node-based diagrams
- **Layout Engine**: elkjs for automatic graph layout algorithms

### Testing
- **Unit Testing**: Vitest
- **E2E Testing**: Playwright
- **Component Testing**: Testing Library (Svelte)
- **DOM Environment**: jsdom for unit tests

### Package Management
- **Package Manager**: npm
- **Node Version**: Node.js 22+ (or 20.19+)
- **Version Management**: `.nvmrc` file for nvm compatibility

## Database & Storage

### Data Storage
- **Primary Storage**: YAML files in dbt project directory
  - `data_model.yml`: Entity and relationship definitions
  - `canvas_layout.yml`: Visual layout/positioning data
- **dbt Artifacts**: Read-only access to dbt-generated files
  - `manifest.json`: dbt project structure and dependencies
  - `catalog.json`: Column metadata and types

### Database (Example/Testing)
- **Default**: DuckDB (via dbt-duckdb adapter)
- **Purpose**: Used for example projects and testing, not required for core functionality

## Development Tools

### Version Control
- **VCS**: Git
- **Hosting**: GitHub
- **CI/CD**: GitHub Actions

### Code Quality
- **Type Checking**: 
  - TypeScript for frontend (`npm run check`)
  - Python type hints for backend
- **Linting/Formatting**: Follow language conventions (no enforced linters yet)

### Build & Distribution
- **Python Build**: setuptools + wheel
- **Frontend Build**: Vite production build (`npm run build`)
- **Package Distribution**: Python wheel with bundled frontend static files
- **Distribution Channel**: PyPI

## Deployment & Infrastructure

### Hosting
- **Platform**: Google Cloud (mentioned in standards, specific services TBD)
- **Deployment Model**: Python package installed locally by users
- **Architecture**: Local-first, no cloud dependencies required

### CI/CD
- **CI Platform**: GitHub Actions
- **Workflows**: 
  - `ci.yml`: Continuous integration (tests, linting)
  - `publish.yml`: Package publishing to PyPI
  - `cla.yml`: CLA verification

## Development Environment

### Prerequisites
- **Python**: 3.11+ with `uv` installed
- **Node.js**: 22+ (or 20.19+) with npm
- **Make**: Optional, for convenience Makefile targets

### Development Setup
- **Backend Dev**: `make backend` or `uv run trellis run` (hot reload)
- **Frontend Dev**: `make frontend` or `cd frontend && npm run dev` (hot reload)
- **Devcontainer**: Supported for WSL/Windows collaboration

### Build Process
- **Frontend Build**: `npm run build` in `frontend/` directory
- **Package Build**: `make build-package` (builds frontend + Python wheel)
- **Output**: Python wheel in `dist/` directory

## Technology Decisions & Rationale

### Why FastAPI?
- Modern, fast Python web framework
- Automatic OpenAPI documentation
- Async support for I/O-bound operations
- Type hints support

### Why SvelteKit?
- Lightweight and performant
- Great developer experience
- Built-in routing and SSR capabilities
- Strong TypeScript support

### Why Tailwind CSS?
- Rapid UI development
- Consistent design system
- Small bundle size with purging
- Excellent documentation

### Why @xyflow/svelte?
- Industry-standard graph visualization library
- Svelte-specific bindings
- Interactive node/edge manipulation
- Extensible and customizable

### Why YAML for Storage?
- Human-readable format
- Easy to version control
- Familiar to dbt users
- No database setup required (local-first)

### Why uv for Python?
- Fast dependency resolution
- Modern Python package management
- Better than pip for development workflows
- Compatible with standard Python packaging

## Future Considerations

### Potential Additions
- **Database**: May add optional database for large projects (PostgreSQL/SQLite)
- **Caching**: Redis for performance optimization (if cloud features added)
- **Authentication**: If collaboration features require it
- **WebSockets**: For real-time collaboration (future)

### Framework Expansion
- **Adapters**: Plugin system for additional transformation frameworks
- **Abstract Interfaces**: Base adapter classes for framework-agnostic core

## Standards & Conventions

See `agent-os/standards/` for detailed coding standards:
- Backend: API design, models, migrations, queries
- Frontend: Components, CSS, accessibility, responsive design
- Global: Coding style, commenting, error handling, validation, testing
