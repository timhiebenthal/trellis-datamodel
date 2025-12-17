# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Enhanced Sidebar error messages to provide clearer instructions for dbt project configuration: now suggests running `dbt docs generate` or `dbt compile` based on catalog existence, and directs users to the "Config Info" button for detailed configuration information
### Fixed
- Fixed cursor visibility issue on WSL/Windows: replaced `grab`/`grabbing` cursors with `default`/`move` cursors, and `text` (I-beam) cursor with `default` cursor to prevent invisible white cursors on light backgrounds

## [0.2.1] - 2025-12-14

### Fixed
- Fixed relationship auto-inference on drag-and-drop for versioned models (e.g., `customer_booking.v1`): the frontend now correctly maps the base model name instead of the version suffix when building the model-to-entity lookup
- Fixed duplicate relationship creation when rebinding models: when a model is unbound and then rebound, the system now reuses the existing generic edge (upgrading it with field mappings) instead of creating a second relationship edge between the same entities
- Fix folder-name filter 

## [0.2.0] - 2025-12-09

### Added
- Added `/api/config-info` endpoint to expose resolved configuration paths for debugging
- Added "Config info" modal in UI to display resolved paths, model directories, and file existence status
- Added clear error message when relationship inference finds no schema yml files in configured model paths
- Added version-aware schema read/write: model schema endpoints now accept an optional version and frontend passes the active model version when fetching/saving YAML
- Adopted GNU Affero General Public License v3.0 and added `LICENSE`/`NOTICE`.
- Added CLA documentation and GitHub Action to enforce CLA signing on pull requests.

### Fixed
- Fixed relationship inference to correctly handle `dbt_model_paths` entries with `models/` prefix (e.g., `models/3_entity`) by normalizing paths to prevent double-prepending
- Fixed frontend static file serving priority - now correctly prefers configured `FRONTEND_BUILD_DIR` over package static directory, ensuring local builds are served during development
- Normalized tag handling in the UI so string values (e.g., model/folder names) no longer explode into per-character tag chips; tag filters now only use real tag arrays
- Fixed relationship auto-inference for versioned models when YAML versions are parsed as integers (e.g., `v: 1`), restoring inferred edges like `player.v1` → `team`
- Fixed saving drafted columns so updates land in the requested dbt model version instead of the latest by default (preserves other versions)

### Changed
- Removed backwards-compatibility alias `_get_models_dir()` in favor of unified `get_model_dirs()` method
- Relationship inference now only includes relationships where both source and target entities have bound dbt models (including `additional_models`), preventing unbound relationships from being written to `data_model.yml` in large-scale projects

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
