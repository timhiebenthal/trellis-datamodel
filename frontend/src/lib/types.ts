export interface DbtColumn {
    name: string;
    type: string;
}

export interface DbtModel {
    name: string;
    schema: string;
    table: string;
    columns: DbtColumn[];
}

export interface EntityData {
    label: string;
    description?: string;
    dbt_model?: string; // name of the bound model
}

// We'll use Svelte Flow types for nodes/edges in the actual components, 
// but for API/Persistence we treat them as generic objects or define a schema.
export interface Ontology {
    version: number;
    entities: any[];
    relationships: any[];
}

