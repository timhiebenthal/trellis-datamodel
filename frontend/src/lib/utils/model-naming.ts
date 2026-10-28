import type { ConfigInfo } from '$lib/types';

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
 * Strip configured entity prefixes from a label.
 *
 * Uses ENTITY_PREFIXES from config-info API response.
 * Strips the first matching prefix from the label while preserving original casing of the remaining text.
 *
 * @param label - The label to strip prefixes from (e.g., "tbl_customer")
 * @param prefixes - Array of prefixes to strip (e.g., ["tbl_", "entity_"])
 * @returns Label with first matching prefix removed (e.g., "customer")
 *
 * @example
 * stripEntityPrefixes("tbl_customer", ["tbl_"]) // "customer"
 * stripEntityPrefixes("TBL_CUSTOMER", ["tbl_"]) // "CUSTOMER" (case-insensitive match, original casing preserved)
 * stripEntityPrefixes("tbl_customer", ["entity_", "tbl_"]) // "customer" (first match removed)
 * stripEntityPrefixes("customer", ["tbl_"]) // "customer" (no match, returns original)
 * stripEntityPrefixes("tbl_", ["tbl_"]) // "" (edge case: label equals prefix, returns empty string)
 * stripEntityPrefixes("tbl_customer", []) // "tbl_customer" (empty prefix array, returns original)
 */
export function stripEntityPrefixes(label: string, prefixes: string[]): string {
    // Handle empty or undefined prefix array gracefully
    if (!prefixes || prefixes.length === 0) {
        return label;
    }
    
    // Handle edge case where label itself is undefined/null
    if (!label) {
        return label;
    }
    
    const lowerLabel = label.toLowerCase();
    
    // Check each prefix for a case-insensitive match
    for (const prefix of prefixes) {
        // Validate prefix is not empty string (warn user in logs)
        if (prefix === "") {
            console.warn(`Invalid empty prefix found in entity_prefixes config. Skipping this prefix.`);
            continue;
        }
        
        if (lowerLabel.startsWith(prefix.toLowerCase())) {
            // Strip prefix and preserve original casing for remainder
            const stripped = label.substring(prefix.length);
            
            // Handle edge case where label equals prefix (empty result after stripping)
            if (stripped === "") {
                console.log(`Entity label "${label}" equals prefix "${prefix}", resulting in empty string. Displaying original label.`);
                return label; // Return original label to avoid empty UI elements
            }
            
            return stripped;
        }
    }
    
    // Log prefix operation for debugging
    if (prefixes.length > 0 && prefixes.some(p => p && p !== "")) {
        console.log(`Stripping prefixes [${prefixes.join(", ")}] from label "${label}"`);
    }
    
    // No prefix matched, return original label
    return label;
}

/**
 * Choose the prefix list that should be stripped from labels for the current modeling style.
 * Falls back to entity_prefix when label_prefixes is not provided.
 */
export function getLabelPrefixesFromConfig(info?: ConfigInfo | null): string[] {
    if (!info) {
        return [];
    }

    if (info.label_prefixes && info.label_prefixes.length > 0) {
        return info.label_prefixes;
    }

    return info.entity_prefix ?? [];
}

/**
 * Infer dimensional entity type from model name using configured prefixes.
 */
export function classifyModelTypeFromPrefixes(
    modelName: string,
    dimensionPrefixes: string[] = [],
    factPrefixes: string[] = [],
): "dimension" | "fact" | null {
    const lower = modelName.toLowerCase();
    for (const p of dimensionPrefixes || []) {
        if (p && lower.startsWith(p.toLowerCase())) {
            return "dimension";
        }
    }
    for (const p of factPrefixes || []) {
        if (p && lower.startsWith(p.toLowerCase())) {
            return "fact";
        }
    }
    return null;
}

/**
 * Format a dbt model name for use as an entity label.
 * Replaces underscores with spaces and title-cases each word.
 * Optionally strips configured prefixes before formatting.
 * 
 * @param modelName - The model name (e.g., "entity_booking" or "tbl_customer")
 * @param prefixes - Optional array of prefixes to strip (e.g., ["tbl_", "entity_"])
 * @returns Formatted label (e.g., "Entity Booking" or "Customer")
 * 
 * @example
 * formatModelNameForLabel("user_id") // "User Id"
 * formatModelNameForLabel("API_key") // "Api Key"
 * formatModelNameForLabel("entity_booking") // "Entity Booking"
 * formatModelNameForLabel("tbl_customer", ["tbl_"]) // "Customer"
 * formatModelNameForLabel("TBL_CUSTOMER", ["tbl_"]) // "Customer"
 * formatModelNameForLabel("tbl_customer", []) // "Tbl Customer" (backward compatible)
 */
export function formatModelNameForLabel(modelName: string, prefixes: string[] = []): string {
    const withoutPrefix = stripEntityPrefixes(modelName, prefixes);
    
    // Format the remaining text by splitting underscores and title-casing
    return withoutPrefix
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

/**
 * Decide whether a generated entity label should keep following the entity ID.
 *
 * We keep the label in sync while it still matches the original generated label
 * or the auto-derived label for the current entity ID. Once a user edits the
 * label independently, name changes should no longer overwrite it.
 */
export function shouldAutoSyncGeneratedEntityLabel(
    currentEntityId: string,
    currentLabel: string,
    originalLabel: string,
    prefixes: string[] = []
): boolean {
    const normalizedCurrentLabel = (currentLabel || '').trim();
    const normalizedOriginalLabel = (originalLabel || '').trim();

    if (!normalizedCurrentLabel) {
        return true;
    }

    if (normalizedCurrentLabel === normalizedOriginalLabel) {
        return true;
    }

    return normalizedCurrentLabel === formatModelNameForLabel(currentEntityId, prefixes).trim();
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
