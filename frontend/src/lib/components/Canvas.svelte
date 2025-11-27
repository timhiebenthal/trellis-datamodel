<script context="module" lang="ts">
    // Track recently created edges to prevent duplicates (persists across component remounts)
    const recentConnections = new Set<string>();
</script>

<script lang="ts">
    import {
        SvelteFlow,
        Controls,
        Background,
        BackgroundVariant,
        MiniMap,
        type Node,
        type Connection,
        type Edge,
    } from "@xyflow/svelte";

    import { nodes, edges } from "$lib/stores";
    import EntityNode from "./EntityNode.svelte";
    import GroupNode from "./GroupNode.svelte";
    import CustomEdge from "./CustomEdge.svelte";
    import Icon from "@iconify/svelte";

    const nodeTypes = {
        entity: EntityNode,
        group: GroupNode,
    };

    const edgeTypes = {
        custom: CustomEdge,
    };

    function getParallelOffset(index: number): number {
        if (index === 0) return 0;
        const level = Math.ceil(index / 2);
        const offset = level * 20;
        return index % 2 === 1 ? offset : -offset;
    }

    function onConnect(connection: Connection) {
        const connectionKey = `${connection.source}-${connection.target}`;
        console.log(`[${Date.now()}] onConnect triggered for ${connectionKey}`, connection);
        
        // Check if this exact connection was just made
        if (recentConnections.has(connectionKey)) {
            console.warn("Blocked duplicate connection:", connectionKey);
            return;
        }
        
        // Mark as recently created, clear after 1 second
        recentConnections.add(connectionKey);
        setTimeout(() => recentConnections.delete(connectionKey), 1000);

        // Check if a generic edge (no field mapping) already exists between these nodes
        // This prevents double creation if the store hasn't updated yet but we have a logical duplicate
        const genericEdgeExists = $edges.some(e => 
            ((e.source === connection.source && e.target === connection.target) ||
             (e.source === connection.target && e.target === connection.source)) &&
            !e.data?.source_field && 
            !e.data?.target_field
        );

        if (genericEdgeExists) {
             console.warn("Blocked duplicate generic edge:", connectionKey);
             return;
        }

        // Generate unique edge ID
        const baseId = `e${connection.source}-${connection.target}`;
        let edgeId = baseId;
        let counter = 1;
        while ($edges.some((e) => e.id === edgeId)) {
            edgeId = `${baseId}-${counter}`;
            counter++;
        }

        const existingBetweenPair = $edges.filter(
            (e) =>
                (e.source === connection.source && e.target === connection.target) ||
                (e.source === connection.target && e.target === connection.source),
        ).length;

        const edge: Edge = {
            id: edgeId,
            source: connection.source!,
            target: connection.target!,
            type: "custom",
            data: {
                label: "",
                type: "one_to_many",
                parallelOffset: getParallelOffset(existingBetweenPair),
                label_dx: 0,
                label_dy: 0,
            },
        };
        console.log("Creating edge:", edge);
        $edges = [...$edges, edge];
    }

    function generateSlug(label: string): string {
        // Convert to lowercase and replace spaces/special chars with underscores
        let slug = label
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "_")
            .replace(/^_+|_+$/g, ""); // trim leading/trailing underscores

        // Ensure uniqueness by checking existing node IDs
        let finalSlug = slug;
        let counter = 1;
        while ($nodes.some((node) => node.id === finalSlug)) {
            finalSlug = `${slug}_${counter}`;
            counter++;
        }

        return finalSlug;
    }

    function addEntity() {
        const label = "New Entity";
        const id = generateSlug(label);
        
        // Find max zIndex to place new entity on top
        // Groups have zIndex 1, entities should start at 10+ to be above groups
        const maxZIndex = Math.max(...$nodes.map(n => n.zIndex || (n.type === "group" ? 1 : 10)), 10);
        
        const newNode: Node = {
            id,
            type: "entity",
            position: {
                x: 100 + Math.random() * 200,
                y: 100 + Math.random() * 200,
            },
            data: {
                label,
                description: "",
                width: 280,
                panelHeight: 200,
                collapsed: false,
            },
            zIndex: maxZIndex + 1, // Place on top of all other nodes
        };
        $nodes = [...$nodes, newNode];
    }

    function onEdgesDelete(deletedEdges: Edge[]) {
        // When an edge is deleted, delete all other edges between the same two entities
        const pairsToCheck = deletedEdges.map((e) => ({
            source: e.source,
            target: e.target,
        }));

        const edgesToRemove = $edges.filter((e) =>
            pairsToCheck.some(
                (pair) =>
                    (e.source === pair.source && e.target === pair.target) ||
                    (e.source === pair.target && e.target === pair.source),
            ),
        );

        if (edgesToRemove.length > 0) {
            const idsToRemove = new Set(edgesToRemove.map((e) => e.id));
            // Ensure we also remove the ones explicitly deleted (though Svelte Flow might handle them)
            deletedEdges.forEach((e) => idsToRemove.add(e.id));

            // Update store
            $edges = $edges.filter((e) => !idsToRemove.has(e.id));
        }
    }
</script>

<div class="flex-1 h-full relative w-full">
    <SvelteFlow
        bind:nodes={$nodes}
        edges={$edges}
        {nodeTypes}
        {edgeTypes}
        onconnect={onConnect}
        onedgesdelete={onEdgesDelete}
        defaultEdgeOptions={{ type: "custom" }}
        fitView
        class="bg-slate-50"
    >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <MiniMap />

        <div class="absolute top-4 right-4 z-10 shadow-lg">
            <button
                class="bg-[#0f172a] text-white px-4 py-2 rounded-lg hover:bg-slate-800 font-medium transition-colors flex items-center gap-2 shadow-sm"
                onclick={addEntity}
            >
                <Icon icon="lucide:plus" class="w-4 h-4" />
                Add Entity
            </button>
        </div>

        {#if $nodes.length === 0}
            <div
                class="absolute inset-0 flex items-center justify-center pointer-events-none z-10"
            >
                <div
                    class="bg-white/90 backdrop-blur-sm p-8 rounded-xl border border-slate-200 shadow-xl text-center max-w-md mx-4"
                >
                    <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                         <Icon icon="lucide:palette" class="w-8 h-8 text-slate-400" />
                    </div>
                    <h3 class="text-xl font-bold text-slate-800 mb-2">
                        Start Designing
                    </h3>
                    <p class="text-slate-600 mb-6">
                        Drag dbt models from the sidebar or create new entities
                        to begin building your data model.
                    </p>
                    <button
                        class="bg-[#0f172a] text-white px-6 py-2.5 rounded-lg hover:bg-slate-800 font-medium transition-colors shadow-md pointer-events-auto flex items-center justify-center gap-2 mx-auto"
                        onclick={addEntity}
                    >
                        <Icon icon="lucide:plus" class="w-4 h-4" />
                        Create First Entity
                    </button>
                </div>
            </div>
        {/if}
    </SvelteFlow>
</div>