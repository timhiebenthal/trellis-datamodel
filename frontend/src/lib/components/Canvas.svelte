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
    import CustomEdge from "./CustomEdge.svelte";

    const nodeTypes = {
        entity: EntityNode,
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
        // Generate unique edge ID (allow multiple edges between same entities)
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
        bind:edges={$edges}
        {nodeTypes}
        {edgeTypes}
        onconnect={onConnect}
        onedgesdelete={onEdgesDelete}
        defaultEdgeOptions={{ type: "custom" }}
        fitView
        class="bg-gray-50"
    >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <MiniMap />

        <div class="absolute top-4 right-4 z-10 shadow-lg">
            <button
                class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 font-medium transition-colors flex items-center gap-2"
                onclick={addEntity}
            >
                <span>+</span> Add Entity
            </button>
        </div>

        {#if $nodes.length === 0}
            <div
                class="absolute inset-0 flex items-center justify-center pointer-events-none z-10"
            >
                <div
                    class="bg-white/80 backdrop-blur-sm p-8 rounded-xl border border-gray-200 shadow-lg text-center max-w-md mx-4"
                >
                    <div class="text-4xl mb-4">🎨</div>
                    <h3 class="text-xl font-semibold text-gray-800 mb-2">
                        Start Designing
                    </h3>
                    <p class="text-gray-600 mb-6">
                        Drag dbt models from the sidebar or create new entities
                        to begin building your data model.
                    </p>
                    <button
                        class="bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 font-medium transition-colors shadow-sm pointer-events-auto"
                        onclick={addEntity}
                    >
                        Create First Entity
                    </button>
                </div>
            </div>
        {/if}
    </SvelteFlow>
</div>

