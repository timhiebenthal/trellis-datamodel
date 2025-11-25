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

    function onConnect(connection: Connection) {
        // Check if a relationship already exists between these two nodes
        const relationshipExists = $edges.some(
            (edge) =>
                (edge.source === connection.source &&
                    edge.target === connection.target) ||
                (edge.source === connection.target &&
                    edge.target === connection.source),
        );

        if (relationshipExists) {
            console.log("Relationship already exists between these nodes");
            return; // Don't create duplicate
        }

        const edge: Edge = {
            id: `e${connection.source}-${connection.target}`,
            source: connection.source!,
            target: connection.target!,
            type: "custom",
            data: {
                label: "",
                type: "one_to_many",
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
</script>

<div class="flex-1 h-full relative w-full">
    <SvelteFlow
        bind:nodes={$nodes}
        bind:edges={$edges}
        {nodeTypes}
        {edgeTypes}
        onconnect={onConnect}
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

<style>
    :global(.svelte-flow__pane) {
        cursor: default !important;
    }
</style>
