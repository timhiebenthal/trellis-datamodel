/**
 * Utility functions for handling folder path operations in the sidebar.
 * Extracted from SidebarGroup component for better testability and reusability.
 */

import type { ModelInfo } from '$lib/types';

/**
 * Extracts the relative folder path by removing the first segment.
 * Used to convert full paths to filterable folder paths.
 * 
 * @param fullPath - The full folder path (e.g., "models/staging/customers")
 * @returns The relative path without the first segment, or empty string if not applicable
 * 
 * @example
 * extractRelativePath("models/staging/customers") // returns "staging/customers"
 * extractRelativePath("models") // returns ""
 * extractRelativePath("") // returns ""
 */
export function extractRelativePath(fullPath: string): string {
    if (!fullPath) return "";
    
    // Remove first segment (everything before and including the first /)
    const relativePath = fullPath.replace(/^[^/]+\//, "");
    
    // Return relative path if it exists and is different from the original
    return relativePath && relativePath !== fullPath ? relativePath : "";
}

/**
 * Toggles a folder filter in the filter array.
 * If the folder is already present, it's removed. Otherwise, it's added.
 * 
 * @param currentFilters - The current array of folder filters
 * @param folderPath - The folder path to toggle
 * @returns A new array with the folder path added or removed
 * 
 * @example
 * toggleFolderFilter(["staging/customers"], "staging/customers") // returns []
 * toggleFolderFilter([], "staging/customers") // returns ["staging/customers"]
 * toggleFolderFilter(["staging/orders"], "staging/customers") // returns ["staging/orders", "staging/customers"]
 */
export function toggleFolderFilter(currentFilters: string[], folderPath: string): string[] {
    const safeFilters = Array.isArray(currentFilters) ? currentFilters : [];
    
    if (safeFilters.includes(folderPath)) {
        return safeFilters.filter((f) => f !== folderPath);
    }
    
    return [...safeFilters, folderPath];
}

/**
 * Extract the canonical folder path from a model's file_path.
 * Returns every directory component below the last "models" segment (or below a
 * leading Bruin "assets" segment), or the normalized path when neither exists.
 * Returns null when the file is directly under "models"/"assets" or has no
 * usable parent directory.
 */
export function getModelFolder(model: ModelInfo): string | null {
    if (!model.file_path) return null;
    const p = model.file_path.replace(/\\/g, '/');
    const lastSlash = p.lastIndexOf('/');
    const dir = lastSlash !== -1 ? p.substring(0, lastSlash) : '';
    let parts = dir.split('/').filter((x) => x !== '.' && x !== '');
    const modelsIndex = parts.lastIndexOf('models');
    if (modelsIndex !== -1) {
        parts = parts.slice(modelsIndex + 1);
    } else if (parts[0] === 'assets') {
        // Bruin: file_path is relative to the pipeline, under assets/
        parts = parts.slice(1);
    }
    return parts.length > 0 ? parts.join('/') : null;
}
