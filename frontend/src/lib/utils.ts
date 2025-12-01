import type { DbtModel } from './types';

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

