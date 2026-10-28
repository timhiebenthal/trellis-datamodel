import type { ModelSchema } from '$lib/types';

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
