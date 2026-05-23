export interface DbtColumn {
    name: string;
    type: string;
    description?: string;
}

export interface DbtModel {
    unique_id: string; // e.g. "model.elmo.entity_booking"
    name: string;
    version?: number | null;
    schema: string;
    table: string;
    columns: DbtColumn[];
    description?: string;
    materialization?: string;
    file_path?: string;
    tags?: string[];
}

export interface TreeNode {
    name: string;
    path: string;
    type: 'folder' | 'file';
    children: TreeNode[]; 
    model?: DbtModel; 
}

export interface ColumnLink {
    sourceColumn: string;      // e.g., "home_team_id"
    targetEntity: string;      // e.g., "team"
    targetColumn: string;      // e.g., "team_id"
}

export interface EntityRole {
    label?: string;
    role?: string;
    source?: string;
}

export interface DraftedField {
    name: string;
    datatype: 'text' | 'int' | 'float' | 'bool' | 'date' | 'timestamp' | 'unknown';
    description?: string;
    origin?: string;
}

export interface EntityData {
    label: string;
    description?: string;
    dbt_model?: string; // unique_id of the bound model (e.g. "model.elmo.entity_booking")
    additional_models?: string[]; // additional dbt models bound to this entity
    drafted_fields?: DraftedField[]; // User-defined fields when no dbt model is bound
    width?: number;
    panelHeight?: number;
    collapsed?: boolean;
    folder?: string; // relative folder path (excluding main path)
    tags?: string[];
    entity_type?: "fact" | "dimension" | "unclassified"; // Entity type for dimensional modeling
    annotation_type?: AnnotationType; // For dimensions: which 7W category (who/what/when/where/how/why)
    source_system?: string[]; // Array of source system names (bound = derived from lineage, unbound = persisted)
    domain?: string; // Optional business domain (supports entities created outside business events)
    domains?: string[]; // Optional multi-domain assignment (dimension can belong to many)
    // Internal tracking for tag sources (not persisted to YAML)
    _schemaTags?: string[]; // Tags explicitly defined in schema.yml
    _manifestTags?: string[]; // Tags from manifest (may include inherited tags)
}

/**
 * Entity as persisted in the data model YAML.
 * This is the serialization format, not the Svelte Flow node format.
 */
export interface Entity {
    id: string;
    label: string;
    description?: string;
    dbt_model?: string;
    additional_models?: string[];
    drafted_fields?: DraftedField[];
    position: { x: number; y: number };
    width?: number;
    panel_height?: number;
    collapsed?: boolean;
    tags?: string[];
    entity_type?: "fact" | "dimension" | "unclassified";
    annotation_type?: AnnotationType; // For dimensions: which 7W category (who/what/when/where/how/why)
    source_system?: string[]; // Only for unbound entities (mock sources)
    domain?: string; // Optional business domain (supports entities created outside business events)
    domains?: string[]; // Optional multi-domain assignment
    /**
     * Role-playing dimensions: list of role objects this dimension can play in business processes.
     *
     * Allows a single dimension entity to represent multiple contextual uses in the business domain,
     * bridging business language and technical dimensional modeling.
     *
     * Examples:
     * - A "Calendar" dimension might have roles: [{ role: "order_date" }, { role: "ship_date" }, { role: "delivery_date" }]
     * - An "Employee" dimension might have roles: [{ role: "sales_agent" }, { role: "manager" }, { role: "team_lead" }]
     * - A "Location" dimension might have roles: [{ role: "store_location" }, { role: "warehouse_location" }, { role: "delivery_address" }]
     *
     * When users annotate business events:
     * - They can select a dimension (e.g., "Calendar")
     * - And optionally assign a specific role (e.g., "order_date")
     * - This creates a richer semantic representation: "Calendar (Order Date)"
     *
     * Roles are purely optional and additive. Existing dimensions and annotations work unchanged.
     *
     * @remarks
     * - Roles are defined by the dimension owner and stored here as EntityRole objects
     * - Annotations reference these roles via the `role` field in AnnotationEntry
     * - Each role object contains label, role, and source fields for extensibility
     * - Deleting a role does not break existing annotations that reference it
     */
    roles?: EntityRole[];
}

/**
 * Relationship as persisted in the data model YAML.
 */
export interface Relationship {
    source: string;
    target: string;
    label?: string;
    type: 'one_to_many' | 'many_to_one' | 'one_to_one' | 'many_to_many';
    source_field?: string;
    target_field?: string;
    label_dx?: number;
    label_dy?: number;
    source_model_name?: string; // name of the source model (e.g., "employee")
    source_model_version?: number | null; // version of the source model if versioned
    target_model_name?: string; // name of the target model (e.g., "employee_history")
    target_model_version?: number | null; // version of the target model if versioned
}

/**
 * The data model structure as persisted in YAML.
 */
export interface DataModel {
    version: number;
    entities: Entity[];
    relationships: Relationship[];
    domains?: Domain[];
    source_colors?: Record<string, string>; // Map of source name to color (from canvas_layout.yml)
}

export interface ConfigStatus {
    config_present: boolean;
    config_filename?: string;
    dbt_project_path: string;
    manifest_path: string;
    catalog_path: string;
    manifest_exists: boolean;
    catalog_exists: boolean;
    data_model_exists: boolean;
    error?: string;
}

export interface GuidanceConfig {
    entity_wizard_enabled: boolean;
    push_warning_enabled: boolean;
    min_description_length: number;
    disabled_guidance: string[];
}

export interface EntityWizardData {
    label: string;
    description: string;
    entity_type?: "fact" | "dimension" | "unclassified";
}

export interface ConfigInfo {
    config_path?: string | null;
    framework: string;
    dbt_project_path: string;
    manifest_path: string;
    manifest_exists: boolean;
    catalog_path: string;
    catalog_exists: boolean;
    data_model_path: string;
    data_model_exists: boolean;
    canvas_layout_path: string;
    canvas_layout_exists: boolean;
    frontend_build_dir: string;
    model_paths_configured: string[];
    model_paths_resolved: string[];
    entity_creation_guidance?: GuidanceConfig;
    guidance?: GuidanceConfig;
    lineage_enabled?: boolean;
    lineage_layers?: string[];
    exposures_enabled?: boolean;
    exposures_default_layout?: 'dashboards-as-rows' | 'entities-as-rows';
    bus_matrix_enabled?: boolean;
    business_events_enabled?: boolean;
    modeling_style?: 'dimensional_model' | 'entity_model';
    entity_prefix?: string[];
    label_prefixes?: string[];
    dimension_prefix?: string[];
    fact_prefix?: string[];
    bruin_pipeline_path?: string;
    bruin_asset_paths?: string[];
    pipeline_path_exists?: boolean;
}

export interface FieldDragState {
    nodeId: string;
    fieldName: string;
    nodeLabel: string;
}

export interface RelationshipTest {
    relationships: {
        arguments?: {
            to: string;
            field: string;
        };
        to?: string;
        field?: string;
    };
}

export interface ModelSchemaColumn {
    name: string;
    data_type?: string;
    description?: string;
    data_tests?: RelationshipTest[];
}

export interface ModelSchema {
    model_name: string;
    description: string;
    columns: ModelSchemaColumn[];
    tags?: string[];
    file_path: string;
}

export interface Exposure {
    name: string;
    label?: string;
    type?: string;
    description?: string;
    owner?: { name?: string };
}

export type EntityUsage = Record<string, string[]>; // entity ID -> exposure names array

export interface ExposuresResponse {
    exposures: Exposure[];
    entityUsage: EntityUsage;
}

export interface LineageNode {
    id: string;
    label: string;
    level: number;
    isSource: boolean;
    sourceName?: string; // Source-name for source nodes (e.g., "mock_csv" from "source.project.mock_csv.table")
    layer?: string; // Layer assignment for lineage organization (e.g., "sources", "1_clean", "2_prep", "unassigned")
}

export interface LineageEdge {
    source: string;
    target: string;
    level: number;
}

export interface LineageMetadata {
    root_model_id: string;
    level_counts: Record<number, number>;
    total_nodes: number;
    total_edges: number;
    lineage_layers?: string[]; // Configured layer order from trellis.yml
}

export interface LineageResponse {
    nodes: LineageNode[];
    edges: LineageEdge[];
    metadata: LineageMetadata;
}

export interface Domain {
    id: string;
    label: string;
    color: string;
    entities: string[];
}

// Config API types
export interface ConfigFieldMetadata {
    type: string;
    enum_values?: string[];
    default: any;
    required: boolean;
    description: string;
    beta: boolean;
}

export interface ConfigSchema {
    fields: Record<string, ConfigFieldMetadata>;
    beta_flags: string[];
}

export interface ConfigGetResponse {
    config: Record<string, any>;
    schema_metadata: ConfigSchema;
    file_info?: {
        path: string;
        mtime: number;
        hash: string;
        backup_path?: string;
    };
    trellis_version?: string;
    error?: string;
}

export interface ConfigUpdateResponse {
    config: Record<string, any>;
    file_info: {
        path: string;
        mtime: number;
        hash: string;
    };
}

// Business Events types
export type BusinessEventType = 'discrete' | 'evolving' | 'recurring';

export type AnnotationType = 'who' | 'what' | 'when' | 'where' | 'how' | 'why' | 'how_many';

export type SevenWType = AnnotationType;

export type SevenWsEntry = AnnotationEntry;

export type BusinessEventSevenWs = BusinessEventAnnotations;

export type Annotation = AnnotationEntry;

export interface AnnotationEntry {
    id: string;
    dimension_id?: string;
    text: string;
    description?: string;
    attributes?: Record<string, any>;
    /**
     * Role name when this annotation represents a specific use of a role-playing dimension.
     *
     * When a dimension supports multiple roles (via Entity.roles), users can specify which role
     * this annotation represents. This adds semantic richness to the business process description.
     *
     * Examples:
     * - dimension_id: "dim_calendar", role: "order_date" → "Calendar (Order Date)"
     * - dimension_id: "dim_employee", role: "sales_agent" → "Employee (Sales Agent)"
     * - dimension_id: "dim_location", role: "warehouse_location" → "Location (Warehouse)"
     *
     * Optional field. When not specified, only the dimension is displayed.
     * The role must be one of the values in the corresponding Entity.roles array (though
     * enforcement is soft - freeform values are allowed for flexibility).
     *
     * @remarks
     * - Role selection is always optional in the UI
     * - Roles are only relevant when dimension_id is specified
     * - Role display format: "Dimension (Role)" in cards and lists
     * - Removing a role from Entity.roles does not break existing annotations
     */
    role?: string;
}

export interface BusinessEventAnnotations {
    who: AnnotationEntry[];
    what: AnnotationEntry[];
    when: AnnotationEntry[];
    where: AnnotationEntry[];
    how: AnnotationEntry[];
    why: AnnotationEntry[];
    how_many: AnnotationEntry[];
}

export interface Dimension {
    id: string;
    label: string;
    entity_type: 'fact' | 'dimension' | 'unclassified' | 'entity' | undefined;
    annotation_type?: AnnotationType;
    description?: string;
}

export interface DerivedEntity {
    entity_id: string;
    created_at: string; // ISO timestamp
}

export interface BusinessEvent {
    id: string; // e.g., "evt_YYYYMMDD_NNN"
    text: string;
    description?: string; // Optional longer description providing more context
    type: BusinessEventType;
    domain?: string; // Optional business domain (e.g., "Sales", "Marketing")
    process_id?: string; // Optional ID of the process this event belongs to
    created_at: string; // ISO timestamp
    updated_at: string; // ISO timestamp
    annotations?: BusinessEventAnnotations; // Event annotations (Who, What, When, Where, How, How Many, Why)
    derived_entities: DerivedEntity[];
}

export interface GeneratedEntitiesResult {
    entities: Array<{
        id: string;
        label: string;
        entity_type: 'fact' | 'dimension' | 'unclassified';
        description?: string;
        metadata?: Record<string, any>;
        tags?: string[]; // Tags including inherited domain tags
        drafted_fields?: DraftedField[]; // Fields for fact tables from how_many annotations
    }>;
    relationships: Array<{
        source: string;
        target: string;
        type: 'one_to_many' | 'many_to_one' | 'one_to_one' | 'many_to_many';
        label?: string;
    }>;
    errors: string[];
}

// Business Event Process types
export interface BusinessEventProcess {
    id: string; // e.g., "proc_YYYYMMDD_NNN"
    name: string;
    description?: string; // Optional longer description providing more context
    type: BusinessEventType;
    domain?: string;
    event_ids: string[];
    created_at: string; // ISO timestamp
    updated_at: string; // ISO timestamp
    resolved_at?: string; // ISO timestamp, when the process was resolved (ungrouped)
    annotations_superset?: BusinessEventAnnotations; // Union of all member event annotations
    derived_entities?: DerivedEntity[]; // Entities generated from this process
}

// Process API request types
export interface CreateProcessRequest {
    name: string;
    type: BusinessEventType;
    description?: string;
    domain: string;
    event_ids?: string[];
}

export interface UpdateProcessRequest {
    name?: string;
    type?: BusinessEventType;
    description?: string | null;
    domain?: string | null;
    annotations_superset?: BusinessEventAnnotations | null;
    event_ids?: string[];
    derived_entities?: DerivedEntity[];
}

export interface AttachEventsRequest {
    event_ids: string[];
}

export interface DetachEventsRequest {
    event_ids: string[];
}

// Entity List View types
export interface EntityListFilters {
    searchTerm: string;
    selectedDomains: string[];
    selectedTags: string[];
    selectedEntityTypes: Array<'dimension' | 'fact' | 'unclassified'>;
    sortDirection: 'asc' | 'desc';
    groupByEntityType: boolean;
}

export interface EntityDetailModalState {
    open: boolean;
    entityId: string | null;
}

export interface BulkEditModalState {
    open: boolean;
    selectedEntityIds: string[];
}
