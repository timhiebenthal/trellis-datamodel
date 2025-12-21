## General development conventions

### Project Structure
- **Backend Code**: Python package in `trellis_datamodel/` directory
  - Routes: `trellis_datamodel/routes/` (FastAPI routers)
  - Models: `trellis_datamodel/models/` (Pydantic schemas)
  - Utils: `trellis_datamodel/utils/` (utility functions)
  - Tests: `trellis_datamodel/tests/` (pytest tests)
- **Frontend Code**: SvelteKit app in `frontend/` directory
  - Components: `frontend/src/lib/` (reusable components)
  - Routes: `frontend/src/routes/` (SvelteKit routes)
  - Tests: `frontend/tests/` (Vitest/Playwright tests)
- **Configuration**: `trellis.yml` for runtime config, `pyproject.toml` for Python package config

### Documentation
- **README**: Maintain up-to-date README.md with setup instructions, architecture overview, and contribution guidelines
- **Code Comments**: Follow commenting standards (see `commenting.md`)
- **API Docs**: FastAPI automatically generates OpenAPI docs at `/docs` endpoint

### Version Control
- **Commit Messages**: Use clear, descriptive commit messages
- **Feature Branches**: Use feature branches for development; main branch should be stable
- **Pull Requests**: Create meaningful PRs with descriptions explaining changes
- **CLA**: All contributors must sign the CLA (see `CLA.md`)

### Environment Configuration
- **Config Files**: Use `trellis.yml` for runtime configuration (dbt paths, etc.)
- **Environment Variables**: Use environment variables for secrets; never commit API keys or secrets
- **Devcontainer**: Project supports devcontainer setup for WSL/Windows collaboration

### Dependency Management
- **Python**: Use `uv` for Python dependency management (`uv sync` to install)
- **Node.js**: Use `npm` for frontend dependencies (`npm install` in `frontend/` directory)
- **Keep Updated**: Keep dependencies up-to-date and minimal; document major dependency choices

### Development Workflow
- **Local Development**: Run backend (`make backend`) and frontend (`make frontend`) separately for hot reload
- **Testing**: Run tests before committing (`make test-all` or individual test commands)
- **Building**: Use `make build-package` to build distribution package

### Release Management
- **Versioning**: Follow semantic versioning (see `pyproject.toml` for current version)
- **Changelog**: Maintain `CHANGELOG.md` to track significant changes and improvements
- **Distribution**: Build Python wheel with bundled frontend for PyPI distribution
