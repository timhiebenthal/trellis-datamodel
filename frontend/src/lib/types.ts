export interface DbtColumn {
    name: string;
    type: string;
}

export interface DbtModel {
    unique_id: string; // e.g. "model.elmo.entity_booking"
    name: string;
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

