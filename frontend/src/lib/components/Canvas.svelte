<script module lang="ts">
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
    import { setContext } from "svelte";
    import { nodes, edges, viewMode, modelingStyle } from "$lib/stores";
    import { getParallelOffset, generateSlug } from "$lib/utils";
    import { DimensionalModelPositioner, GroupSizeCalculator } from "$lib/services/position-calculator";
    import EntityNode from "./EntityNode.svelte";
    import GroupNode from "./GroupNode.svelte";
    import CustomEdge from "./CustomEdge.svelte";
    import EntityCreationWizard from "./EntityCreationWizard.svelte";
    import Icon from "$lib/components/Icon.svelte";
    import type { GuidanceConfig, EntityWizardData } from "$lib/types";
    import { writable } from "svelte/store";

    const nodeTypes = {
        entity: EntityNode,
        group: GroupNode,
    };

    const edgeTypes = {
        custom: CustomEdge,
    };

    // Props
    let {
        guidanceConfig,
        lineageEnabled = false,
        exposuresEnabled = false,
        hasExposuresData = false,
    }: { guidanceConfig: GuidanceConfig; lineageEnabled?: boolean; exposuresEnabled?: boolean; hasExposuresData?: boolean } = $props();

    const lineageEnabledStore = writable(lineageEnabled);
    setContext("lineageEnabled", lineageEnabledStore);

    const exposuresEnabledStore = writable(exposuresEnabled);
    setContext("exposuresEnabled", exposuresEnabledStore);

    const hasExposuresDataStore = writable(hasExposuresData);
    setContext("hasExposuresData", hasExposuresDataStore);

    $effect(() => {
        lineageEnabledStore.set(lineageEnabled);
    });

    $effect(() => {
        exposuresEnabledStore.set(exposuresEnabled);
    });

    $effect(() => {
        hasExposuresDataStore.set(hasExposuresData);
    });

    // Wizard state
    let wizardOpen = $state(false);
    let wizardData = $state<EntityWizardData | null>(null);

    // Position calculator services
    const positioner = new DimensionalModelPositioner();
    const groupSizeCalculator = new GroupSizeCalculator();

    function onConnect(connection: Connection) {
        const connectionKey = `${connection.source}-${connection.target}`;
        console.log(
            `[${Date.now()}] onConnect triggered for ${connectionKey}`,
            connection,
        );

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
        const genericEdgeExists = $edges.some(
            (e) =>
                ((e.source === connection.source &&
                    e.target === connection.target) ||
                    (e.source === connection.target &&
                        e.target === connection.source)) &&
                !e.data?.source_field &&
                !e.data?.target_field,
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
                (e.source === connection.source &&
                    e.target === connection.target) ||
                (e.source === connection.target &&
                    e.target === connection.source),
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

    function addEntity() {
        // Check if wizard is enabled
        if (guidanceConfig?.entity_wizard_enabled) {
            wizardOpen = true;
            return;
        }

        // Create entity immediately if wizard is disabled
        createEntityWithData({
            label: "New Entity",
            description: "",
        });
    }

    function createEntityWithData(data: EntityWizardData) {
        const label = data.label || "New Entity";
        const id = generateSlug(label, $nodes.map((n) => n.id));

        // Find max zIndex to place new entity on top
        // Groups have zIndex 1, entities should start at 10+ to be above groups
        const maxZIndex = Math.max(
            ...$nodes.map((n) => n.zIndex || (n.type === "group" ? 1 : 10)),
            10,
        );

        // Calculate smart position based on entity type and modeling style
        let position: { x: number; y: number };

        if ($modelingStyle === "dimensional_model" && data.entity_type) {
            // Smart positioning for dimensional modeling
            position = calculateSmartPosition(data.entity_type);
        } else {
            // Default random positioning
            position = {
                x: 100 + Math.random() * 200,
                y: 100 + Math.random() * 200,
            };
        }

        const newNode: Node = {
            id,
            type: "entity",
            position,
            data: {
                label,
                description: data.description || "",
                entity_type: data.entity_type || "unclassified",
                width: 280,
                panelHeight: 200,
                collapsed: false,
            },
            zIndex: maxZIndex + 1, // Place on top of all other nodes
        };
        $nodes = [...$nodes, newNode];
    }

    function calculateSmartPosition(entityType: "fact" | "dimension" | "unclassified"): { x: number; y: number } {
        // Use positioner service for smart positioning
        return positioner.calculateSmartPosition(entityType, $nodes);
    }

    function handleWizardComplete(data: EntityWizardData) {
        wizardOpen = false;
        createEntityWithData(data);
    }

    function handleWizardCancel() {
        wizardOpen = false;
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

    // Track dragging state to prevent updates interrupting drag
    let isDragging = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    function onNodeDragStart(params: any) {
        console.log("Drag start:", params.node?.id);
        isDragging = true;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    function onNodeDragStop(params: any) {
        console.log("Drag stop:", params.node?.id);
        isDragging = false;
        // Force update after drag
        updateGroupSizes();
    }

    // Auto-resize groups to fit children
    function updateGroupSizes() {
        // Use group size calculator service
        const result = groupSizeCalculator.calculateGroupSizes(
            $nodes,
            $viewMode as "conceptual" | "logical",
            isDragging,
        );

        if (result.needsUpdate) {
            $nodes = groupSizeCalculator.applyGroupSizes($nodes, result.sizes);
        }
    }

    $effect(() => {
        // Track nodes and viewMode to trigger updates
        const _ = $nodes;
        const __ = $viewMode;

        // Run immediately
        updateGroupSizes();

        // Run after a delay to catch layout updates (e.g. after expand animation/render)
        const timer1 = setTimeout(updateGroupSizes, 50);
        const timer2 = setTimeout(updateGroupSizes, 300);

        return () => {
            clearTimeout(timer1);
            clearTimeout(timer2);
        };
    });
</script>

<div class="flex-1 h-full relative w-full">
    <SvelteFlow
        bind:nodes={$nodes}
        edges={$edges}
        {nodeTypes}
        {edgeTypes}
        onconnect={onConnect}
        ondelete={(params) => params.edges && onEdgesDelete(params.edges)}
        onnodedragstart={onNodeDragStart}
        onnodedragstop={onNodeDragStop}
        defaultEdgeOptions={{ type: "custom" }}
        fitView
        panOnDrag={true}
        selectionOnDrag={false}
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
                    <div
                        class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4"
                    >
                        <Icon
                            icon="lucide:palette"
                            class="w-8 h-8 text-slate-400"
                        />
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

    <!-- Floating View Mode Switcher - Only show on canvas (conceptual/logical views) -->
    {#if $viewMode === "conceptual" || $viewMode === "logical"}
        <div
            class="absolute bottom-14 left-1/2 transform -translate-x-1/2 z-20 pointer-events-auto inline-flex items-center bg-white rounded-full border border-primary-500 shadow-md relative overflow-hidden transition-all duration-150 px-1 w-auto"
            style="box-shadow: 0 0 6px rgba(13, 148, 136, 0.25);"
        >
            <!-- Conceptual Option -->
            <button
                type="button"
                class="px-3 py-2 text-sm font-semibold flex items-center gap-2 transition-all duration-150 border-0 bg-transparent cursor-pointer"
                class:text-primary-600={$viewMode === "conceptual"}
                class:text-gray-500={$viewMode !== "conceptual"}
                class:hover:text-gray-900={$viewMode !== "conceptual"}
                onclick={() => ($viewMode = "conceptual")}
                title="Conceptual View"
            >
                <Icon icon="octicon:workflow-16" class="w-3.5 h-3.5" />
                Conceptual
            </button>

            <!-- Vertical Divider -->
            <div class="w-[1px] h-7 bg-gray-200"></div>

            <!-- Logical Option -->
            <button
                type="button"
                class="px-3 py-2 text-sm font-semibold flex items-center gap-2 transition-all duration-150 border-0 bg-transparent cursor-pointer"
                class:text-primary-600={$viewMode === "logical"}
                class:text-gray-500={$viewMode !== "logical"}
                class:hover:text-gray-900={$viewMode !== "logical"}
                onclick={() => ($viewMode = "logical")}
                title="Logical View"
            >
                <Icon icon="lucide:database" class="w-3.5 h-3.5" />
                Logical
            </button>
        </div>
    {/if}

    <!-- Entity Creation Wizard -->
    <EntityCreationWizard
        open={wizardOpen}
        onComplete={handleWizardComplete}
        onCancel={handleWizardCancel}
        existingEntityIds={$nodes.filter((n) => n.type === "entity").map((n) => n.id)}
        config={guidanceConfig}
    />
</div>
