# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-01-29

### Added
- Added Business Events modeling based on the **7 Ws methodology** (Who, What, When, Where, How, How Many, Why) using the BEAM* approach.
- Added a new **Business Events view** (`/business-events`) for managing and visualizing business processes.
- Added a structured **7 Ws Form** for capturing event details with enhanced annotations, descriptions, and examples.
- Added **Automated Entity Generation**: automatically derive star schemas (fact and dimension tables) from defined business events and processes.
- Added **Dimension Autocomplete** component to link events to existing dimensions or propose new ones.
- Added **Event Card** and **Event Filter Banner** components for improved organization and discovery of business events.
- Added `business_events.yml` support for persisting event definitions alongside the data model.
- Added backend service layer (`BusinessEventsService`, `EntityGenerator`, `BusinessEventProcessService`) to handle event logic and dbt artifact generation.
- Added comprehensive test suites for business events logic, including Vitest for frontend components and pytest for backend services.
- Added **Business Event Grouping**: users can now multi-select business events and group them into named processes for consolidated modeling.
- Added process creation modal with name, type, and domain selection (discrete/evolving/recurring) for organizing related events.
- Added process-level 7W annotation union logic that automatically combines annotations from all member events using unique key deduplication.
- Added process badges in the business events list to visually indicate grouped events.
- Added process detail panel showing member events and the unified 7W superset annotations.
- Added process resolution functionality to ungroup events while preserving all original event data and maintaining history fields.
- Added `processes` section to `business_events.yml` for storing process definitions with metadata (`id`, `name`, `type`, `domain`, `event_ids`, timestamps).
- Added optional `process_id` field on business events to link events to their parent process.
- Added API endpoints for creating, updating, resolving, and listing processes.
- Added service methods for recomputing process-level annotation supersets when events are edited or re-linked.
- Extended entity generation to support process-level inputs:
  - `discrete` process type generates a single fact table with per-event records (`event_id`/`process_id` columns).
  - `evolving` process type generates accumulating snapshot modeling with status and time columns.
- Added **Drag-and-Drop Event Reordering**: users can now reorder events within processes using intuitive drag-and-drop interactions with visual feedback indicators.
- Added **Process Editing Modal**: edit process details (name, type, domain) directly from the business events view.
- Added **CollapseChevron** component for consistent expansion/collapse UI patterns across the application.
- Added enhanced annotation type descriptions and examples in the 7 Ws Form for improved user guidance.
- Added **Deep Clone Support** for Svelte 5 Proxy objects to ensure proper state management in history functions and auto-save operations.
- Added domain-based filtering for organizing events and processes by business domain.
- Added support for generating dimensional entities directly from business event processes with process-aware entity tagging.

### Changed
- Refactored the annotation system to transition from unstructured text highlights to structured event-based modeling.
- Updated the main navigation and layout to include the Business Events view.
- Enhanced `trellis.yml` configuration to support business event metadata and storage paths.
- Updated the ERD Canvas to visualize relationships derived from business events.
- Updated business events list UI to support multi-select functionality, domain filtering, and process-based organization.
- Enhanced entity generation service to accept process-level inputs in addition to individual events.
- Improved 7 Ws Form with clearer annotations, better descriptions, and consistent ordering across components.
- Refactored BusinessEvents component to support domain grouping, drag-and-drop reordering, and process management.
- Enhanced drag event handling in Canvas component for more accurate node positioning during interactions.

### Fixed
- Fixed various edge cases in relationship inference when dealing with multi-model entities.
- Improved frontend state management for auto-saving complex form data in the 7 Ws wizard.
- Fixed process annotation superset recomputation when events are edited after grouping to maintain data integrity.
- Fixed node drag event handling to use accurate target tracking and synchronize edges correctly during drag operations.
- Fixed annotation type ordering for consistency across all form components.
- Fixed tooltip visibility in SevenWsForm by adjusting z-index layering.

## [0.7.0]

### Added
- Added configurable entity prefix support for entity modeling mode to maintain table naming conventions while keeping labels clean.
- Added `entity_modeling.inference_patterns.prefix` configuration option to `trellis.yml` supporting single string or list of strings for prefix values. Defaults to empty list (no prefix) for backward compatibility.
- Added automatic prefix application when saving unbound entities to dbt schema.yml files (uses first configured prefix).
- Added case-insensitive prefix detection to prevent duplication (e.g., `TBL_CUSTOMER` won't become `tbl_TBL_CUSTOMER`).
- Added automatic prefix stripping from entity labels displayed on ERD canvas for improved readability.
- Added support for multiple prefix patterns (e.g., `["tbl_", "entity_", "t_"]`) to handle legacy naming conventions.
- Added preservation of bound dbt_model values to avoid re-prefixed entities that already have prefixes.
- Added `/api/config-info` endpoint response field `entity_prefix` to expose configured prefixes to frontend.
- Added web-based Configuration UI page (`/config`) for viewing and editing `trellis.yml` settings with form-based editing, real-time validation, automatic backups, and conflict detection.
- Added `POST /api/config/reload` endpoint to reload configuration at runtime without server restart, clearing adapter inference cache when config changes.
- Added entity source chips feature: entities now support a `sources` field (list of strings) persisted in `data_model.yml` for manual source tracking (e.g., "Salesforce", "ERP").
- Added source visualization: sources displayed as colorful chips in entity node headers with configurable color mapping via `source_colors` in `canvas_layout.yml`.
- Added lineage-derived source suggestions: source editor suggests values based on existing sources and technical lineage from bound dbt models (read-only hints).
- Added distinct routes for main views (`/canvas`, `/exposures`, `/bus-matrix`) enabling bookmarking, reloading, and sharing specific views with browser history support.
- Added interactive CLI wizard for `trellis init` command that guides users through configuring `trellis.yml` with sensible defaults and auto-detection capabilities.
- Added dbt models header in sidebar with branded header section and favicon below filter divider.
- Added entity type icons in sidebar: color-coded icons based on model type (green for dimensions, blue for facts, gray for unclassified) in dimensional modeling mode.
- Added advanced filtering in sidebar for dimensional modeling mode: entity type filter (dimension/fact/unclassified) and model bound filter (bound/unbound).
- Added unified `.inline-input` CSS class for consistent styling of tag and source editors across the app.
- Added comprehensive E2E test helpers for config manipulation (`getConfig()`, `saveConfig()`, `reloadConfig()`) and test isolation utilities.
- Added frontend unit tests for `inferRelationships` API function with Vitest.

### Changed
- Extended Entity TypedDict in backend with prefix-aware model name generation via `_entity_to_model_name()` method.
- Updated frontend label formatting to strip configured prefixes from entity names while preserving original casing of remaining text.
- Entity prefix feature only activates when `modeling_style` is `entity_model` (default).
- Refactored frontend configuration state management: switched from hardcoded/local state to context-based store pattern in `+layout.svelte` for reactive configuration values across components.
- Changed default `modeling_style` to `entity_model` in `trellis.yml` for standardization.
- Relocated "Apply Configuration" and "Reset Changes" buttons to top of Config page for better visibility and accessibility.
- Updated schema API endpoints to use path parameters (`/models/{model}/schema`) instead of query params.
- Changed header navigation to use standard anchor tags (`<a href="/canvas">`) instead of state-based button clicks for route-aware view switching.
- Updated frontend to automatically synchronize `$viewMode` store with current route via `$effect` in shared layout.
- Refactored backend architecture: created dedicated service layer (`trellis_datamodel/services/`) separating business logic from route handlers, with routes becoming thin validation/response marshaling layers.
- Consolidated request/response/data models in `trellis_datamodel/models/schemas.py` for reuse across routes/services.
- Extracted frontend business logic into focused service classes (AutoSave, EntityValidation, SchemaManager, PositionCalculator) with clear single responsibilities.
- Reduced major component sizes: `+page.svelte` (~40% reduction), `EntityNode.svelte` (~30% reduction), `Canvas.svelte` (~20% reduction).
- Updated sidebar to display color-coded icons based on modeling style and model type classification.
- Made compact navbar buttons (reduced padding and text size) to create more screen real estate.
- Updated CLI wizard to reorder sections in generated `trellis.yml` for better organization.

### Fixed
- Added validation for prefix configuration to ensure it's a string or list of strings.
- Added error handling for empty prefix lists to maintain backward compatibility.
- Fixed lineage button in `EntityNode.svelte`: added `stopPropagation` to prevent unintended node selection/dragging when opening lineage modal.
- Fixed exposures navigation: exposures button now properly navigates to `/exposures` route and sets view mode.
- Fixed relationship inference logic: refined filtering to allow relationships where both ends are present in data model, even if one or both are unbound.
- Updated `inferRelationships` API function to handle both array and object-wrapped payloads for improved robustness.
- Fixed relationship inference to correctly handle entities defined in data model but not strictly "bound" to primary dbt model.
- Fixed config reload to properly clear adapter inference cache when configuration changes.
- Fixed schema API to use path parameters for better RESTful design.
- Added proper error handling for config reload endpoint with user-friendly error messages.
- Fixed exposures button visibility: now correctly hidden when `exposures.enabled: false` in `trellis.yml`.
- Fixed canvas edge styling: lighter gray edges that don't compete with node colors, improved z-index handling for edge labels.
- Fixed relationship test references in `dbt_company_dummy_kimball/models/3_core/dim_employee.yml`.
- Fixed smart guidance toggle: automatically disables "push warning" setting when "entity creation guidance" is toggled off.
- Added graceful fallbacks for route navigation: `/exposures` and `/bus-matrix` redirect to `/canvas` if features are disabled or no data exists.

## [0.6.0]

### Added
- Added native support for Kimball dimensional modeling with entity classification (fact/dimension/unclassified) and smart default positioning for star/snowflake schemas.
- Added `modeling_style` configuration option to `trellis.yml` with values `dimensional_model` and `entity_model` (default for backward compatibility).
- Added configurable inference patterns for automatic entity type classification from dbt model naming: `dimensional_modeling.inference_patterns` with `dimension_prefix` and `fact_prefix`.
- Added Kimball Bus Matrix view mode displaying dimensions as rows and facts as columns with checkmarks for connections.
- Added Bus Matrix filter controls for dimensions, facts, and tags with real-time filtering.
- Added entity type indicators (icons/badges) on entity nodes with color coding: blue for fact, green for dimension, gray for unclassified.
- Added smart default positioning logic: facts placed in canvas center, dimensions in outer ring when `modeling_style` is `dimensional_model`.
- Added "Auto-Layout" button to toolbar to reposition entities according to fact/dimension rules.
- Added entity type selection step to Entity Creation Wizard with radio buttons and descriptions.
- Added context menu options to change entity type (Set as Fact/Set as Dimension/Set as Unclassified).
- Added entity type badge click handler with dropdown menu for quick type changes.
- Added Bus Matrix navigation button to main navigation bar alongside Canvas and Exposures views.
- Added Bus Matrix icon badge to entity nodes linking to pre-filtered matrix view for that entity.
- Added tooltips for entity type badges explaining each type's meaning.

### Changed
- Extended Entity TypedDict in backend with optional `entity_type` field ("fact", "dimension", "unclassified").
- Extended frontend Entity interface with `entity_type` field.
- Updated `/data-model` GET endpoint to include `entity_type` in entity data.
- Updated `/data-model` POST endpoint to persist `entity_type` changes.
- Added `/bus-matrix` GET endpoint returning dimensions, facts, and connections with optional filtering by domain, tag, fact_id, or dimension_id.
- Entity type inference only activates when `modeling_style` is `dimensional_model`.
- Existing entity positions from `canvas_layout.yml` are preserved during smart positioning.
- Manual positioning overrides are respected (not overwritten by auto-layout unless explicitly requested).

### Fixed
- Added validation for `entity_type` field values against allowed enum (fact/dimension/unclassified).
- Added error handling for invalid entity_type submissions with user-friendly error messages.
- Added graceful handling for Bus Matrix endpoint errors (missing relationships, empty data model, invalid query parameters).
- Added smooth CSS transitions for entity position changes to prevent jarring UI jumps.
- Added debouncing to Bus Matrix filter inputs for improved performance with large datasets.

## [0.5.0] - 2026-01-07

### Added
- Added a new "Exposures" view mode that provides a cross-table visualization of entity usage across downstream dbt exposures.
- Added support for fetching and displaying exposure metadata (labels, types, owners, descriptions) from the backend API.
- Added automated empty state handling for projects without `exposures.yml` with helpful guidance for users.
- Added exposures view feature flag (`exposures.enabled`) to optionally disable Exposures view; exposures can be enabled via `trellis.yml` configuration (default: false, opt-in).
- Added transposed table layout for exposures view with manual toggle button; default layout shows dashboards as rows and entities as columns for improved readability when dashboards outnumber tables or have longer names.
- Added `exposures.default_layout` configuration option to set initial table orientation; values are `dashboards-as-rows` (default) or `entities-as-rows`.
- Added layout toggle button in Exposures view to switch between orientations without persistence (resets to default on page reload).
- Added API guard returning 403 Forbidden when exposures feature is disabled to avoid unnecessary data processing and improve performance for organizations not using exposures.
- Added support for progressive header density (normal/narrow/angled) to entity column headers when in transposed layout.

### Changed
- Added `lineage.enabled` feature flag (default: false) with nested `lineage.layers` configuration; top-level `lineage_layers` remains supported with deprecation warning. Lineage UI and API routes are now disabled unless explicitly enabled.
- Added `guidance.entity_wizard.enabled` feature flag (default: true) so the entity creation wizard mirrors the nested feature-flag style; the loader still honors legacy `guidance.entity_wizard_enabled` for compatibility.
- Renamed guidance block to `entity_creation_guidance` with flat `enabled`; `guidance`, `entity_wizard_enabled`, and `entity_creation_guidance.wizard.enabled` remain supported with deprecation warnings.
- Improved floating view mode switcher in canvas: restructured from nested buttons to single button with vertical divider bar, increased height by ~30%, and refined styling for better user experience.
- Exposures view is now opt-in (disabled by default) to reduce UI noise for organizations that don't use downstream exposure tracking in dbt.
- Backend config-info endpoint now exposes `exposures_enabled` and `exposures_default_layout` for frontend consumption.

### Fixed
- Fixed exposures not loading: added missing `import json` statement that was causing manifest loading to fail silently
- Fixed exposures.yml file location detection: now checks project root directory (`dbt_concept/exposures.yml`) in addition to `models/exposures.yml`
- Improved exposure loading to read from manifest.json first (canonical source with resolved model references), then fallback to YAML file

## [0.4.0] - 2025-01-15

### Added
- Added upstream table-level lineage visualization: users can now double-click on any entity bound to a dbt model to view its upstream lineage in a modal overlay. The lineage graph shows all upstream models back to source tables, using dbt-colibri for lineage extraction. The modal includes zoom controls, minimap navigation, and progressive display of lineage levels. Requires `dbt docs generate` to be run for full lineage enrichment via catalog.json.
- Added auto-naming for entities when binding dbt models: when a user binds a dbt model to an unnamed entity (ID starts with `new_entity` and label is `"New Entity"`), the entity ID and label are automatically derived from the dbt model name. Model names are formatted with title-case and spaces (e.g., `entity_booking` → `"Entity Booking"`), and the entity ID is generated as a slugified version. This reduces manual naming steps and improves developer experience.
- Added layer-based organization for lineage visualization: lineage views now support horizontal layer bands based on dbt folder structure. Configure `lineage_layers` in `trellis.yml` with an ordered list of folder names (e.g., `["1_clean", "2_prep", "3_core"]`) to group models into semantic transformation stages. Models are automatically assigned to layers based on their folder path, with sources displayed at the top and unassigned models at the bottom. Layer bands are displayed with light background shading and labels on the left side, providing visual organization without obscuring the graph. Configuration is optional and backward compatible - projects without `lineage_layers` config display lineage without layers.
- Added guided entity creation wizard: when creating new entities, users are guided through a 3-step wizard (Entity Name → Description → Optional Attributes) to ensure well-documented entity definitions. The wizard includes real-time validation, example descriptions, and character counters. Users can skip steps or dismiss the wizard entirely. Configure via `guidance.entity_wizard_enabled` in `trellis.yml` (default: true).
- Added push-to-dbt warning for incomplete entities: before syncing to dbt, users are warned if any entities are missing descriptions. The warning modal lists affected entities and allows users to cancel or continue. This helps prevent syncing incomplete entity definitions. Configure via `guidance.push_warning_enabled` in `trellis.yml` (default: true). Additional guidance settings include `guidance.min_description_length` (default: 10 characters) and `guidance.disabled_guidance` array to disable specific guidance features.
- Added checkmark indicators in sidebar for dbt models bound to entities: the sidebar now displays a checkmark icon next to dbt models that are already bound to entities, making it easy to identify which models still need to be modeled. Checkmarks appear on the right side of model items and update reactively when entities are bound or unbound. Models bound via either the primary `dbt_model` field or `additional_models` array show the same checkmark indicator.

## [0.3.5] - 2025-12-23

### Added
- Added relationship deduplication for entities with multiple dbt models: when an entity has multiple dbt models (e.g., `employee` and `employee_history`), relationships are now aggregated into a single edge per entity pair instead of showing parallel edges. The relationship detail box dynamically shows field-level details based on the currently selected dbt model for each entity.

### Fixed
- Fixed self-relationship rendering: self-relationships (self-joins) now render as smooth curved loops on the right side of nodes instead of going through the box
- Fixed duplicate relationship tests when converting old syntax (`to:` and `field:` at top level) to new `arguments:` syntax: old-style keys are now properly skipped during conversion, preventing duplicate relationship tests in dbt schema files
- Fixed relationship detail box to show correct model names when switching between multiple dbt models bound to the same entity (e.g., switching from `employee` to `employee_history` now correctly updates the field labels in relationship details)
- Fixed relationship direction swap functionality: the swap button now only changes the relationship type (e.g., `one_to_many` ↔ `many_to_one`) without swapping source/target entities, correctly moving the foreign key between entities and propagating changes to dbt schema files
- Fixed stale relationship test cleanup: when relationship types change (e.g., from `one_to_many` to `many_to_one`), relationship tests are now properly removed from the old FK location and added to the new FK location in dbt schema files

### Changed
- Improved relationship text display: entity names in relationship labels are now shown in quotes (e.g., `one 'department' relates to many 'employee'`) for better readability

## [0.3.4] - 2025-12-21

### Fixed
- Fixed `schema.yml` write-back so empty tag arrays are not written (and existing empty tags are removed), preventing noisy `tags: []` / `config: { tags: [] }` output.
- Fixed tag propagation for dbt models so inherited/manifest tags are displayed but not persisted back into `schema.yml`.
- Fixed relationship test updates to preserve existing relationship-test metadata (e.g. tags) when rebuilding the `relationships` test block.

### Added
- Added internal tag source tracking in the UI to distinguish schema tags (explicit) from manifest tags (inherited) so saves are deterministic.
- Added regression tests covering tag handling and config placement in YAML write-back.

## [0.3.3] - 2025-12-18

### Fixed
- Fixed `trellis generate-company-data` failing when config file exists but `dbt_company_dummy_path` is not configured: the config loader no longer sets a default path, allowing the CLI's smart fallback logic to properly check if `./dbt_company_dummy/generate_data.py` exists in the current working directory

### Added
- Added comprehensive CLI tests (`test_cli.py`) to catch path resolution bugs that only manifest in installed packages. Tests cover `trellis init`, `trellis run`, `trellis generate-company-data`, and help output

## [0.3.2] - 2025-12-17

### Fixed
- Fixed `trellis generate-company-data` fallback path resolution: when run from an installed package without a configured `dbt_company_dummy_path`, the command now prefers `./dbt_company_dummy` in the current working directory instead of looking relative to the installed package.

## [0.3.1] - 2025-12-17

### Fixed
- Fixed configuration variable access to use live values from config module instead of stale copies: CLI commands and API routes now correctly access configuration paths after `load_config()` is called, ensuring `trellis generate-company-data` and other commands work correctly when the package is installed (not just when running from source)

## [0.3.0] - 2025-12-17

### Added
- Added global expand/collapse toggle button in the top bar to expand or collapse all entity nodes at once, with state persisted in browser localStorage across page reloads
- Extended company dummy data generator with procurement domain entities (suppliers, purchase orders, supplier invoices, inventory)
- Added customer invoices and employee/department entities to company dummy data generator
- Company dummy data now showcases two distinct business domains (Sales and Procurement)

### Changed
- Renamed `purchase` to `sale` and `receipt` to `supplier_invoice` in company dummy data for clarity
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
