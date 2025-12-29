export interface DbtColumn {
    name: string;
    type: string;
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

export interface DraftedField {
    name: string;
    datatype: 'text' | 'int' | 'float' | 'bool' | 'date' | 'timestamp';
    description?: string;
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
    source_system?: string[]; // Array of source system names (bound = derived from lineage, unbound = persisted)
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
    source_system?: string[]; // Only for unbound entities (mock sources)
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

