/**
 * Utilities for computing edge highlight states based on node selection.
 * Designed to be reusable across LineageEdge and CustomEdge components.
 */

export interface EdgeHighlightState {
    isSelected: boolean;
    isConnectedToSelectedNode: boolean;
    isVisible: boolean;
    highlightLevel: 'none' | 'connected' | 'selected';
}

/**
 * Check if a node ID represents a placeholder node
 * Placeholder nodes ("...") represent collapsed intermediate nodes in lineage graphs
 * and should not trigger edge highlighting
 */
export function isPlaceholderNode(nodeId: string): boolean {
    return typeof nodeId === 'string' && nodeId.startsWith('placeholder-');
}

/**
 * Check if a node is visible (not hidden)
 */
export function isNodeVisible(node: { hidden?: boolean }): boolean {
    return !node.hidden;
}

/**
 * Check if a node is a valid model node (not a placeholder or layer band)
 */
export function isValidModelNode(nodeId: string, nodeType?: string): boolean {
    if (isPlaceholderNode(nodeId)) return false;
    if (nodeType === 'layerBand') return false;
    return true;
}

/**
 * Compute edge highlight state based on selection and visibility
 * Returns highlight level: 'none', 'connected' (to selected node), or 'selected' (edge itself selected)
 * Only highlights edges connected to visible, non-placeholder nodes
 */
export function computeEdgeHighlightState(
    edge: { id: string; source: string; target: string; selected?: boolean },
    selectedNodeIds: Set<string>,
    getNode: (id: string) => { hidden?: boolean; type?: string } | undefined
): EdgeHighlightState {
    const isSelected = edge.selected === true;
    
    // Check if source or target is selected
    const sourceSelected = selectedNodeIds.has(edge.source);
    const targetSelected = selectedNodeIds.has(edge.target);
    const isConnectedToSelectedNode = sourceSelected || targetSelected;
    
    // Check visibility - both nodes must be visible
    const sourceNode = getNode(edge.source);
    const targetNode = getNode(edge.target);
    const sourceVisible = sourceNode ? isNodeVisible(sourceNode) : true;
    const targetVisible = targetNode ? isNodeVisible(targetNode) : true;
    const isVisible = sourceVisible && targetVisible;
    
    // Determine highlight level
    let highlightLevel: 'none' | 'connected' | 'selected' = 'none';
    if (isSelected) {
        highlightLevel = 'selected';
    } else if (isConnectedToSelectedNode && isVisible) {
        // Only highlight if connected AND visible
        // Also check that nodes are valid (not placeholders)
        const sourceValid = isValidModelNode(edge.source, sourceNode?.type);
        const targetValid = isValidModelNode(edge.target, targetNode?.type);
        if (sourceValid && targetValid) {
            highlightLevel = 'connected';
        }
    }
    
    return {
        isSelected,
        isConnectedToSelectedNode: isConnectedToSelectedNode && isVisible,
        isVisible,
        highlightLevel,
    };
}

/**
 * Get all node IDs that are connected to selected nodes via visible edges
 * Used to highlight connected nodes with a ring when their neighbor is selected
 * Excludes placeholders, hidden nodes, and layer bands
 */
export function getConnectedNodeIds(
    selectedNodeIds: Set<string>,
    edges: Array<{ source: string; target: string }>,
    getNode: (id: string) => { hidden?: boolean; type?: string } | undefined
): Set<string> {
    const connectedIds = new Set<string>();
    
    for (const edge of edges) {
        const sourceSelected = selectedNodeIds.has(edge.source);
        const targetSelected = selectedNodeIds.has(edge.target);
        
        if (sourceSelected || targetSelected) {
            // Check visibility and validity
            const sourceNode = getNode(edge.source);
            const targetNode = getNode(edge.target);
            
            const sourceVisible = sourceNode ? isNodeVisible(sourceNode) : true;
            const targetVisible = targetNode ? isNodeVisible(targetNode) : true;
            const sourceValid = isValidModelNode(edge.source, sourceNode?.type);
            const targetValid = isValidModelNode(edge.target, targetNode?.type);
            
            if (sourceSelected && targetVisible && targetValid) {
                connectedIds.add(edge.target);
            }
            if (targetSelected && sourceVisible && sourceValid) {
                connectedIds.add(edge.source);
            }
        }
    }
    
    return connectedIds;
}

