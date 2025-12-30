import type { DbtModel, Relationship, ModelSchema, ModelSchemaColumn } from './types';
import type { Edge } from '@xyflow/svelte';

/**
 * Calculate parallel offset for multiple edges between the same pair of nodes.
 * Index 0 = center, then alternates above/below.
 */
export function getParallelOffset(index: number): number {
    if (index === 0) return 0;
    const level = Math.ceil(index / 2);
    const offset = level * 20;
    return index % 2 === 1 ? offset : -offset;
}

/**
 * Generate a URL-safe slug from a label, ensuring uniqueness against existing IDs.
 */
export function generateSlug(label: string, existingIds: string[], currentId?: string): string {
    // Convert to lowercase and replace spaces/special chars with underscores
    let slug = label
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, ''); // trim leading/trailing underscores

    // If empty after cleaning, use a default
    if (!slug) slug = 'entity';

    // Ensure uniqueness by checking existing IDs (excluding current if provided)
    let finalSlug = slug;
    let counter = 1;
    while (existingIds.some((id) => id === finalSlug && id !== currentId)) {
        finalSlug = `${slug}_${counter}`;
        counter++;
    }

    return finalSlug;
}

/**
 * Convert a string to title case (capitalize first letter of each word).
 * 
 * @param text - The text to convert
 * @returns Title-cased text
 * 
 * @example
 * toTitleCase("customer order") // "Customer Order"
 * toTitleCase("API_KEY") // "Api Key"
 * toTitleCase("hello world") // "Hello World"
 */
export function toTitleCase(text: string): string {
    if (!text) return text;
    return text
        .split(/\s+/)
        .map(word => {
            if (!word) return word;
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        })
        .join(' ');
}

/**
 * Format a dbt model name for use as an entity label.
 * Replaces underscores with spaces and title-cases each word.
 * 
 * @param modelName - The model name (e.g., "entity_booking")
 * @returns Formatted label (e.g., "Entity Booking")
 * 
 * @example
 * formatModelNameForLabel("user_id") // "User Id"
 * formatModelNameForLabel("API_key") // "Api Key"
 * formatModelNameForLabel("entity_booking") // "Entity Booking"
 */
export function formatModelNameForLabel(modelName: string): string {
    return modelName
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

/**
 * Extract model name from a dbt model's unique_id.
 * Handles both regular and versioned models.
 * 
 * @param uniqueId - The dbt model unique_id (e.g., "model.project.entity_booking" or "model.project.entity_booking.v1")
 * @returns The extracted model name (e.g., "entity_booking")
 * 
 * @example
 * extractModelNameFromUniqueId("model.project.entity_booking") // "entity_booking"
 * extractModelNameFromUniqueId("model.project.entity_booking.v1") // "entity_booking"
 */
export function extractModelNameFromUniqueId(uniqueId: string): string {
    const parts = uniqueId.split(".");
    if (parts.length >= 3 && parts[0] === "model") {
        const lastPart = parts[parts.length - 1];
        const isVersioned = /^v\d+$/.test(lastPart);
        
        if (isVersioned && parts.length >= 4) {
            // Versioned model: return base name (second-to-last part)
            return parts[parts.length - 2];
        } else {
            // Regular model: return last part
            return lastPart;
        }
    }
    // Fallback: if format doesn't match, try to extract from end
    return uniqueId.includes(".") ? uniqueId.split(".").pop()! : uniqueId;
}

/**
 * Extract folder path from a dbt model's file_path.
 * Skips "models/" prefix and the first directory level (e.g., "3_core").
 * Returns null if no subfolder exists.
 */
export function getModelFolder(model: DbtModel): string | null {
    if (!model.file_path) return null;
    let p = model.file_path.replace(/\\/g, '/');
    const lastSlash = p.lastIndexOf('/');
    const dir = lastSlash !== -1 ? p.substring(0, lastSlash) : '';
    let parts = dir.split('/').filter((x) => x !== '.' && x !== '');
    if (parts[0] === 'models') parts.shift();
    // Skip the main folder (first part after models/)
    if (parts.length > 1) {
        parts.shift();
        return parts.join('/');
    }
    return null;
}

/**
 * Normalize any incoming tag shape (string | string[] | undefined) into a
 * clean, deduplicated array of non-empty strings. Prevents single strings
 * from being treated as iterables (which would otherwise explode into
 * characters when spread or flatMapped).
 */
export function normalizeTags(raw: unknown): string[] {
    if (!raw) return [];

    const toStrings = (vals: unknown[]): string[] =>
        vals
            .map((v) => String(v).trim())
            .filter((v) => v.length > 0);

    if (Array.isArray(raw)) {
        return Array.from(new Set(toStrings(raw)));
    }

    if (typeof raw === 'string') {
        // Support comma-separated lists while still accepting single tokens
        const parts = raw.split(',').map((p) => p.trim()).filter(Boolean);
        return Array.from(new Set(parts));
    }

    return [];
}

/**
 * Aggregate relationships by entity pair and create edges.
 * Deduplicates relationships so each entity pair has only one edge,
 * with aggregated model information stored in the edge data.
 */
export function aggregateRelationshipsIntoEdges(relationships: Relationship[]): Edge[] {
    // Group relationships by entity pair (sorted for consistency)
    const relationshipsByPair = new Map<string, Relationship[]>();
    
    relationships.forEach((r) => {
        // Create a consistent key for the entity pair (always sorted)
        const pairKey =
            r.source < r.target
                ? `${r.source}-${r.target}`
                : `${r.target}-${r.source}`;
        
        if (!relationshipsByPair.has(pairKey)) {
            relationshipsByPair.set(pairKey, []);
        }
        relationshipsByPair.get(pairKey)!.push(r);
    });

    // Create one edge per entity pair with aggregated model information
    return Array.from(relationshipsByPair.entries()).map(([pairKey, rels]) => {
        // Use the first relationship for base properties (direction, label, etc.)
        const firstRel = rels[0];
        // Normalize direction: always use source < target for the key, but preserve actual direction
        const actualSource = firstRel.source;
        const actualTarget = firstRel.target;
        
        // Aggregate model information from all relationships
        const models = rels.map((r) => ({
            source_model_name: r.source_model_name,
            source_model_version: r.source_model_version ?? null,
            target_model_name: r.target_model_name,
            target_model_version: r.target_model_version ?? null,
            source_field: r.source_field,
            target_field: r.target_field,
        }));

        const edgeId = `e${actualSource}-${actualTarget}`;

        return {
            id: edgeId,
            source: actualSource,
            target: actualTarget,
            type: "custom",
            data: {
                label: firstRel.label || "",
                type: firstRel.type || "one_to_many",
                // Store first relationship's fields for backward compatibility
                // These will be overridden by active model selection
                source_field: firstRel.source_field,
                target_field: firstRel.target_field,
                label_dx: firstRel.label_dx || 0,
                label_dy: firstRel.label_dy || 0,
                parallelOffset: 0, // No parallel edges anymore
                // Store aggregated model information
                models: models,
                modelCount: models.length,
            },
        } as Edge;
    });
}

/**
 * Merge a new relationship into existing edges, aggregating by entity pair.
 * If an edge already exists for the entity pair, add the relationship to its models array.
 * Otherwise, create a new edge.
 */
export function mergeRelationshipIntoEdges(
    edges: Edge[],
    relationship: Relationship
): Edge[] {
    const pairKey =
        relationship.source < relationship.target
            ? `${relationship.source}-${relationship.target}`
            : `${relationship.target}-${relationship.source}`;
    
    const existingEdge = edges.find((e) => {
        const ePairKey =
            e.source < e.target
                ? `${e.source}-${e.target}`
                : `${e.target}-${e.source}`;
        return ePairKey === pairKey;
    });

    if (existingEdge) {
        // Add this relationship to the existing edge's models array
        const existingModels = (existingEdge.data?.models as any[]) || [];
        const newModel = {
            source_model_name: relationship.source_model_name,
            source_model_version: relationship.source_model_version ?? null,
            target_model_name: relationship.target_model_name,
            target_model_version: relationship.target_model_version ?? null,
            source_field: relationship.source_field,
            target_field: relationship.target_field,
        };
        
        // Check if this exact model relationship already exists
        const modelExists = existingModels.some(
            (m) =>
                m.source_model_name === newModel.source_model_name &&
                m.source_model_version === newModel.source_model_version &&
                m.target_model_name === newModel.target_model_name &&
                m.target_model_version === newModel.target_model_version &&
                m.source_field === newModel.source_field &&
                m.target_field === newModel.target_field
        );
        
        if (!modelExists) {
            return edges.map((e) => {
                if (e.id !== existingEdge.id) return e;
                return {
                    ...e,
                    data: {
                        ...(e.data || {}),
                        models: [...existingModels, newModel],
                        modelCount: existingModels.length + 1,
                        // Update default fields if not set
                        source_field: e.data?.source_field || relationship.source_field,
                        target_field: e.data?.target_field || relationship.target_field,
                    },
                };
            });
        }
        return edges; // Relationship already exists
    } else {
        // Create new edge
        const actualSource = relationship.source;
        const actualTarget = relationship.target;
        const edgeId = `e${actualSource}-${actualTarget}`;
        
        const newEdge: Edge = {
            id: edgeId,
            source: actualSource,
            target: actualTarget,
            type: "custom",
            data: {
                label: relationship.label || "",
                type: relationship.type || "one_to_many",
                source_field: relationship.source_field,
                target_field: relationship.target_field,
                label_dx: relationship.label_dx || 0,
                label_dy: relationship.label_dy || 0,
                parallelOffset: 0,
                models: [
                    {
                        source_model_name: relationship.source_model_name,
                        source_model_version: relationship.source_model_version ?? null,
                        target_model_name: relationship.target_model_name,
                        target_model_version: relationship.target_model_version ?? null,
                        source_field: relationship.source_field,
                        target_field: relationship.target_field,
                    },
                ],
                modelCount: 1,
            },
        };
        
        return [...edges, newEdge];
    }
}

/**
 * Detect field semantics (FK/PK) from model schemas.
 * 
 * This function determines whether a field is a foreign key (FK) or primary key (PK)
 * by examining dbt relationship tests in schema definitions.
 * 
 * Detection Algorithm:
 * 1. FK Detection: Check if the field has a `relationships` test defined in its own schema.
 *    - A field with a relationship test is a foreign key that references another table.
 * 
 * 2. PK Detection: Check if the field is referenced by the other model's relationship tests.
 *    - If another model's field has a relationship test pointing to this field, then this field is a PK.
 *    - Parses `ref('model_name')` format to match the referenced model.
 * 
 * Fallback Behavior:
 * - Returns 'unknown' when:
 *   - Schema is missing for either model
 *   - Field is not found in schema
 *   - Field has no relationship tests and is not referenced
 *   - Relationship test format cannot be parsed
 * 
 * Edge Cases Handled:
 * - Missing schemas: Returns 'unknown' (caller should use drag direction)
 * - Missing fields: Returns 'unknown' (caller should use drag direction)
 * - Both fields are PKs: Returns 'unknown' (caller should use drag direction)
 * - Both fields are FKs: Returns 'unknown' (caller should use drag direction)
 * - Legacy test format: Supports both `arguments` block and top-level keys
 * 
 * @param modelName - Name of the model containing the field
 * @param fieldName - Name of the field to check
 * @param otherModelName - Name of the other model in the relationship (for PK detection)
 * @param modelSchemas - Map of model names to their schemas
 * @returns 'fk' if field is a foreign key, 'pk' if referenced as primary key, 'unknown' otherwise
 */
export function detectFieldSemantics(
    modelName: string,
    fieldName: string,
    otherModelName: string,
    modelSchemas: Map<string, ModelSchema>
): 'fk' | 'pk' | 'unknown' {
    // Check if field is FK (has relationship test)
    const modelSchema = modelSchemas.get(modelName);
    if (modelSchema) {
        const column = modelSchema.columns.find(col => col.name === fieldName);
        if (column?.data_tests) {
            for (const test of column.data_tests) {
                if (test.relationships) {
                    return 'fk';
                }
            }
        }
    }

    // Check if field is PK (referenced by the other model's relationship tests)
    const otherSchema = modelSchemas.get(otherModelName);
    if (otherSchema) {
        for (const column of otherSchema.columns) {
            if (!column.data_tests) continue;
            
            for (const test of column.data_tests) {
                if (test.relationships) {
                    const rel = test.relationships;
                    // Support both recommended arguments block and legacy top-level keys
                    const toRef = rel.arguments?.to || rel.to;
                    const refField = rel.arguments?.field || rel.field;
                    
                    // Check if this relationship references our model and field
                    if (toRef && refField === fieldName) {
                        // Parse ref('model_name') format
                        const refMatch = toRef.match(/ref\(['"]?([^'"]+)['"]?\)/);
                        if (refMatch && refMatch[1] === modelName) {
                            return 'pk';
                        }
                    }
                }
            }
        }
    }

    return 'unknown';
}

