import type { Node } from '@xyflow/svelte';

export type OriginEntry = Record<string, string>;

/** A 2D coordinate (canvas position, edge endpoint, label anchor, ...). */
export interface Point {
    x: number;
    y: number;
}

export interface DbtColumn {
    name: string;
    type: string;
    description?: string;
    origin?: OriginEntry[];
}

export interface ModelInfo {
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
    model?: ModelInfo;
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
    origin?: OriginEntry[];
    source?: 'dbt' | 'draft';
    physical_datatype?: string; // exact type from the framework's catalog, preserved so push doesn't downgrade to the `datatype` bucket
}

// A type alias (not an interface) so it satisfies Svelte Flow's
// `Node<Data extends Record<string, unknown>>` constraint.
export type EntityData = {
    label: string;
    description?: string;
    model_ref?: string; // unique_id of the bound model (e.g. "model.elmo.entity_booking")
    additional_models?: string[]; // additional models bound to this entity
    drafted_fields?: DraftedField[]; // User-defined fields when no model is bound
    width?: number;
    panelHeight?: number;
    collapsed?: boolean;
    folder?: string | null; // relative folder path (excluding main path); null when the bound model has none
    // For a bound entity, `tags` is a computed display union (framework_tags + ui_tags)
    // sent by the backend — never persisted, never hand-edited. Unbound entities
    // persist `tags` directly as their single, freely-editable field.
    tags?: string[];
    framework_tags?: string[]; // Bound entities only: framework-mirrored, reconcile-owned, read-only
    ui_tags?: string[]; // Bound entities only: tags explicitly added via the Trellis tag editor
    entity_type?: "fact" | "dimension" | "unclassified"; // Entity type for dimensional modeling
    annotation_type?: AnnotationType; // For dimensions: which 7W category (who/what/when/where/how/why)
    source_system?: string[]; // Array of source system names (bound = derived from lineage, unbound = persisted)
    domain?: string; // Optional business domain (supports entities created outside business events)
    domains?: string[]; // Optional multi-domain assignment (dimension can belong to many)
    roles?: EntityRole[]; // Role-playing dimensions (see Entity.roles)
};

/**
 * Data on a canvas entity node: the entity fields plus the active-model fields
 * EntityNode publishes for its edges (ephemeral; never persisted).
 */
export type EntityNodeData = EntityData & {
    _activeModelId?: string | null;
    _activeModelName?: string | null;
    _activeModelVersion?: number | null;
};

/** Data on a canvas folder group node. */
export type GroupNodeData = {
    label: string;
    description?: string;
    width?: number;
    height?: number;
    collapsed?: boolean;
    manuallyResized?: boolean;
};

/**
 * Canvas nodes, discriminated by Svelte Flow's `type` (which lives on the node,
 * not in `data`). The `nodes` store stays `Node[]`; narrow with `isEntityNode`.
 */
export type EntityFlowNode = Node<EntityNodeData, 'entity'>;
export type GroupFlowNode = Node<GroupNodeData, 'group'>;

export function isEntityNode(node: Node): node is EntityFlowNode {
    return node.type === 'entity';
}

/**
 * Entity as persisted in the data model YAML.
 * This is the serialization format, not the Svelte Flow node format.
 */
export interface Entity {
    id: string;
    label: string;
    description?: string;
    model_ref?: string;
    additional_models?: string[];
    drafted_fields?: DraftedField[];
    position: Point;
    width?: number;
    panel_height?: number;
    collapsed?: boolean;
    tags?: string[]; // Unbound entities only: single, freely-editable field
    framework_tags?: string[]; // Bound entities only: framework-mirrored, reconcile-owned
    ui_tags?: string[]; // Bound entities only: tags explicitly added via the Trellis tag editor
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

/** One model-level relationship aggregated onto a canvas edge (`edge.data.models`). */
export type RelationshipEdgeModel = Pick<
    Relationship,
    | 'source_model_name'
    | 'source_model_version'
    | 'target_model_name'
    | 'target_model_version'
    | 'source_field'
    | 'target_field'
>;

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

/** One of the active framework's metadata files, as reported by its adapter. */
export interface FrameworkArtifact {
    label: string;
    path: string;
    exists: boolean;
    hint: string;
}

/**
 * What the active framework supports. Gate optional UI on these rather than on
 * `framework`, so adding an adapter never means adding a name check here.
 */
export interface FrameworkCapabilities {
    lineage: boolean;
    column_lineage: boolean;
    exposures: boolean;
    relationships: boolean;
    scaffolding: boolean;
}

export interface ConfigStatus {
    config_present: boolean;
    config_filename?: string;
    framework: string;
    project_path: string;
    project_path_exists: boolean;
    artifacts_present: boolean;
    artifacts: Record<string, FrameworkArtifact>;
    capabilities: FrameworkCapabilities;
    data_model_exists: boolean;
    error?: string | null;
    // Legacy dbt-named keys, absent for frameworks with no manifest/catalog.
    dbt_project_path?: string;
    manifest_path?: string;
    catalog_path?: string;
    manifest_exists?: boolean;
    catalog_exists?: boolean;
}

export interface GuidanceConfig {
    entity_wizard_enabled: boolean;
    push_warning_enabled: boolean;
    min_description_length: number;
    disabled_guidance: string[];
}

export interface CanvasDefaultFilters {
    domains: string[];
    tags: string[];
}

export interface EntityWizardData {
    label: string;
    description: string;
    entity_type?: "fact" | "dimension" | "unclassified";
}

export interface ConfigInfo {
    config_path?: string | null;
    trellis_version?: string;
    framework: string;
    project_path: string;
    project_path_exists: boolean;
    artifacts_present: boolean;
    artifacts: Record<string, FrameworkArtifact>;
    capabilities: FrameworkCapabilities;
    // Legacy dbt-named keys, absent for frameworks with no manifest/catalog.
    dbt_project_path?: string;
    manifest_path?: string;
    manifest_exists?: boolean;
    catalog_path?: string;
    catalog_exists?: boolean;
    data_model_path: string;
    data_model_exists: boolean;
    canvas_layout_path: string;
    canvas_layout_exists: boolean;
    frontend_build_dir: string;
    model_paths_configured: string[];
    model_paths_resolved: string[];
    entity_creation_guidance?: GuidanceConfig;
    guidance?: GuidanceConfig;
    start_page?: 'canvas' | 'entity-list';
    canvas_default_filters?: CanvasDefaultFilters;
    lineage_enabled?: boolean;
    lineage_layers?: string[];
    exposures_enabled?: boolean;
    exposures_default_layout?: 'dashboards-as-rows' | 'entities-as-rows';
    bus_matrix_enabled?: boolean;
    business_events_enabled?: boolean;
    metrics_enabled?: boolean;
    modeling_style?: 'dimensional_model' | 'entity_model';
    entity_prefix?: string[];
    label_prefixes?: string[];
    dimension_prefix?: string[];
    fact_prefix?: string[];
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
    // Set by getConfig() when the request fails (the API answers 4xx/5xx);
    // the API's success body never carries it.
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
    selectedBuildStatus: Array<'bound' | 'unbound'>;
    sortDirection: 'asc' | 'desc';
    groupByEntityType: boolean;
}

/** Canvas domain/tag filter selection (same key names as `EntityListFilters`). */
export interface CanvasFilterState {
    selectedDomains: string[];
    selectedTags: string[];
}

// Metric Tree types

/**
 * A metric on the metric canvas: authored in Trellis (draft) or bound to the
 * semantic model (bound). Drafts carry `expression`; bound entries carry
 * `binding` only.
 */
export interface MetricEntry {
    id: string;
    label: string;
    description?: string;
    expression?: string;
    dataset_ref?: string; // semantic-model dataset the draft is written under; drafts only
    binding?: { dataset: string; name: string }; // semantic_model.yml reference; bound only
    position?: Point; // optional runtime canvas position override
    unresolved?: boolean; // set by GET when dataset_ref or binding no longer resolves
    // Set by GET for a bound metric whose definition resolves: the expression read
    // from semantic_model.yml. Display only; never sent back on save.
    resolved_expression?: string;
}

/**
 * A directed claim: `effect` moves when its `drivers` move.
 */
export interface MetricInfluence {
    effect: string;
    drivers: string[];
}

/**
 * The metric tree as persisted in metric_tree.yml, and the POST payload shape.
 */
export interface MetricTreeFile {
    version: number;
    metrics: MetricEntry[];
    influences: MetricInfluence[];
}

/**
 * One metric found in semantic_model.yml, resolved against the data model.
 * `bindable` is false for cross-dataset metrics and for datasets with no bound entity.
 */
export interface MetricCatalogEntry {
    name: string;
    dataset?: string | null;
    entity_id?: string | null;
    bindable: boolean;
    reason?: string; // present when not bindable
}

/**
 * GET /api/metric-tree: the tree plus what the sidebar and the dataset picker use.
 * `datasets` are the ones a push writes to semantic_model.yml, so they are what a
 * draft's `dataset_ref` can name.
 */
export interface MetricTreeResponse extends MetricTreeFile {
    catalog: MetricCatalogEntry[];
    datasets: string[];
}

/**
 * Data carried by a metric node. The canvas and the node component both read it.
 */
export interface MetricNodeData {
    metric: MetricEntry;
    unresolved: boolean;
}

/**
 * Canvas node for a metric.
 */
export interface MetricTreeNode {
    id: string;
    type: 'metric';
    position: Point;
    data: MetricNodeData;
}

/**
 * Canvas edge for an influence, drawn from the driver to the effect.
 */
export interface MetricTreeEdge {
    id: string;
    type: 'influence';
    source: string;
    target: string;
}
