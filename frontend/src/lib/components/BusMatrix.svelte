<script lang="ts">
    // Placeholder data - will be replaced with API data in Wave 2
    //
    // Performance Optimization Notes for Large Datasets:
    // 1. Debounce filter inputs (to be added in Wave 2): Use a 300ms debounce delay
    //    to avoid re-rendering the matrix on every keystroke.
    // 2. Virtual scrolling: Consider implementing for 100+ dimensions/facts.
    //    Libraries like svelte-virtual-list or tanstack-virtual can render only visible rows.
    // 3. Memoization: Use $: to memoize connection checks and reduce recalculations.
    // 4. Web Workers: Offload relationship building to web worker for 1000+ entities.
    //
    // Target: Render BUS Matrix within 1 second for 100 dimensions × 50 facts.
    const placeholderDimensions = [
        { id: 'dim_1', name: 'Customer' },
        { id: 'dim_2', name: 'Product' },
        { id: 'dim_3', name: 'Date' },
        { id: 'dim_4', name: 'Location' }
    ];

    const placeholderFacts = [
        { id: 'fct_1', name: 'Sales' },
        { id: 'fct_2', name: 'Orders' },
        { id: 'fct_3', name: 'Inventory' }
    ];

    const placeholderConnections = [
        { dimension: 'dim_1', fact: 'fct_1' },
        { dimension: 'dim_1', fact: 'fct_2' },
        { dimension: 'dim_2', fact: 'fct_1' },
        { dimension: 'dim_2', fact: 'fct_2' },
        { dimension: 'dim_3', fact: 'fct_1' },
        { dimension: 'dim_3', fact: 'fct_2' },
        { dimension: 'dim_4', fact: 'fct_1' }
    ];

    function hasConnection(dimensionId: string, factId: string): boolean {
        return placeholderConnections.some(
            conn => conn.dimension === dimensionId && conn.fact === factId
        );
    }
</script>

<div class="bus-matrix-container">
    <div class="bus-matrix-header">
        <div class="flex items-start justify-between">
            <div>
                <h2 class="text-2xl font-bold text-gray-800">BUS Matrix</h2>
                <p class="text-sm text-gray-600 mt-1">View relationships between dimensions and facts</p>
            </div>
            <div class="bus-matrix-help bg-blue-50 border border-blue-200 rounded-md p-3 text-sm max-w-xs">
                <div class="font-medium text-blue-900 mb-1">BUS Matrix Help</div>
                <ul class="text-blue-800 space-y-1 text-xs">
                    <li class="flex items-start gap-2">
                        <span class="text-blue-600 font-bold">✓</span>
                        <span>Checkmark: Dimension connected to this fact</span>
                    </li>
                    <li class="flex items-start gap-2">
                        <span class="text-blue-600 font-bold">○</span>
                        <span>Empty: No connection exists</span>
                    </li>
                    <li class="flex items-start gap-2">
                        <span class="text-blue-600 font-bold">→</span>
                        <span>Click cell to highlight relationship on canvas</span>
                    </li>
                </ul>
            </div>
        </div>
    </div>

    <div class="bus-matrix-table-wrapper">
        <table class="bus-matrix-table">
            <thead>
                <tr>
                    <th class="corner-header">Dimensions / Facts</th>
                    {#each placeholderFacts as fact}
                        <th class="fact-header">{fact.name}</th>
                    {/each}
                </tr>
            </thead>
            <tbody>
                {#each placeholderDimensions as dimension}
                    <tr>
                        <td class="dimension-row">{dimension.name}</td>
                        {#each placeholderFacts as fact}
                            <td class="matrix-cell">
                                {#if hasConnection(dimension.id, fact.id)}
                                    <span class="checkmark">✓</span>
                                {:else}
                                    <span class="empty-circle">○</span>
                                {/if}
                            </td>
                        {/each}
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>
</div>

<style>
    /* Performance note: For datasets with 100+ dimensions/facts, consider implementing
     * virtual scrolling (e.g., using svelte-virtual-list or tanstack-virtual)
     * to render only visible rows/columns. This can significantly improve performance
     * for large matrices by reducing DOM nodes from O(n×m) to O(visible).
     * Current implementation uses sticky positioning which works well for moderate sizes. */

    .bus-matrix-container {
        padding: 20px;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .bus-matrix-header {
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e5e7eb;
    }

    .bus-matrix-table-wrapper {
        overflow-x: auto;
        min-height: 400px;
        max-height: 600px;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        /* Hardware acceleration for smoother scrolling on large tables */
        transform: translateZ(0);
        will-change: transform;
    }

    .bus-matrix-table {
        width: 100%;
        border-collapse: collapse;
        min-width: 600px;
    }

    .bus-matrix-table th,
    .bus-matrix-table td {
        padding: 12px;
        text-align: center;
        border: 1px solid #e5e7eb;
        font-size: 14px;
    }

    .corner-header {
        position: sticky;
        left: 0;
        top: 0;
        background-color: #f9fafb;
        font-weight: bold;
        color: #374151;
        border-right: 2px solid #d1d5db;
        z-index: 20;
        min-width: 200px;
    }

    .fact-header {
        position: sticky;
        top: 0;
        background-color: #f3f4f6;
        font-weight: bold;
        color: #1f2937;
        z-index: 10;
    }

    .dimension-row {
        position: sticky;
        left: 0;
        background-color: #f9fafb;
        font-weight: 600;
        color: #374151;
        text-align: left;
        border-right: 2px solid #d1d5db;
        z-index: 10;
        min-width: 200px;
    }

    .matrix-cell {
        background-color: white;
        cursor: pointer;
        /* Hardware acceleration for hover effects */
        will-change: background-color;
    }

    .matrix-cell:hover {
        background-color: #f3f4f6;
    }

    .checkmark {
        color: #3b82f6;
        font-size: 20px;
        font-weight: bold;
    }

    .empty-circle {
        color: #9ca3af;
        font-size: 18px;
    }
</style>

