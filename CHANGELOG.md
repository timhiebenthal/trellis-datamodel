# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added `/api/config-info` endpoint to expose resolved configuration paths for debugging
- Added "Config info" modal in UI to display resolved paths, model directories, and file existence status
- Added clear error message when relationship inference finds no schema yml files in configured model paths

### Fixed
- Fixed relationship inference to correctly handle `dbt_model_paths` entries with `models/` prefix (e.g., `models/3_entity`) by normalizing paths to prevent double-prepending
- Fixed frontend static file serving priority - now correctly prefers configured `FRONTEND_BUILD_DIR` over package static directory, ensuring local builds are served during development
- Fixed relationship auto-inference for versioned models when YAML versions are parsed as integers (e.g., `v: 1`), restoring inferred edges like `player.v1` → `team`

### Changed
- Removed backwards-compatibility alias `_get_models_dir()` in favor of unified `get_model_dirs()` method

## [0.1.6] - 2025-12-07

### Added
- Relationship inference now supports dbt `relationships` tests that use the `arguments` block, matching dbt’s official syntax
- Added regression test to cover inference from `arguments`-based relationship definitions
- Regression test ensuring the server serves `index.html` from a configured frontend build directory

### Fixed
- Backend now prefers the configured frontend build dir when bundled static assets are missing, so `/` serves the UI instead of returning 404 when running from source
- Relationship inference now ignores malformed `relationships` tests that are missing `to`/`field`, preventing blank-source edges and noisy debug output

### Changed
- Updated header branding to use lowercase "trellis" for consistency
- Replaced iconify box icon with trellis_squared.svg logo in header

## [0.1.5] - 2025-12-06

### Fixed
- Fixed relationship persistence to dbt schema.yml files - relationships now correctly use bound dbt model names instead of entity IDs when writing relationship tests
- Fixed relationship auto-inference from existing dbt tests - adapter now properly loads config and maps model names (including additional_models) to entity IDs
- Fixed adapter factory to use live config values instead of stale module-level constants, ensuring inference works after config is loaded

### Added
- Added trellis_squared.svg as favicon and header logo
- Logo is now bundled as an asset for reliable loading in production
- Added regression tests for relationship sync and inference, including support for additional_models and bound/unbound entities

### Changed
- Updated header branding to use lowercase "trellis" for consistency
- Replaced iconify box icon with trellis_squared.svg logo in header

## [0.1.4] - 2025-12-05

### Fixed
- Fixed frontend API calls to use relative URL (`/api`) instead of hardcoded `localhost:8000`, allowing the app to work on any port
- Improved CLI error message to show full expected path when trellis.yml is not found

## [0.1.3] - 2025-12-05

### Fixed
- Fixed config-status API endpoint to use CONFIG_PATH from startup instead of re-searching from current working directory

## [0.1.2] - 2025-12-05

### Fixed
- Fixed frontend error message to correctly display "Missing `trellis.yml`" instead of "Missing `config.yml`"
- Updated `/api/config-status` endpoint to use `CONFIG_PATH` set at server startup instead of re-checking `os.getcwd()` at request time
- Added `config_filename` field to config status API response to dynamically show the expected config file name

## [0.1.1] - 2025-12-04

- Updated Readme

## [0.1.0] - Initial Release

- Initial release of Trellis Data Model Editor
- Visual data model editor for dbt projects
- Support for conceptual and logical views
- Canvas-based entity relationship diagramming
- Integration with dbt manifest and catalog files
- Support for both `trellis.yml` and `config.yml` configuration files
