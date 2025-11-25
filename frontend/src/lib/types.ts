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
    drafted_fields?: DraftedField[]; // User-defined fields when no dbt model is bound
    width?: number;
    panelHeight?: number;
    collapsed?: boolean;
}

// We'll use Svelte Flow types for nodes/edges in the actual components, 
// but for API/Persistence we treat them as generic objects or define a schema.
export interface Ontology {
    version: number;
    entities: any[];
    relationships: any[];
}

export interface ConfigStatus {
    config_present: boolean;
    dbt_project_path: string;
    manifest_path: string;
    catalog_path: string;
    manifest_exists: boolean;
    catalog_exists: boolean;
    ontology_exists: boolean;
    error?: string;
}

