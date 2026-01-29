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
    import { goto } from "$app/navigation";
    import { nodes, edges, viewMode, modelingStyle } from "$lib/stores";
    import { getParallelOffset, generateSlug } from "$lib/utils";
    import { DimensionalModelPositioner, GroupSizeCalculator } from "$lib/services/position-calculator";
    import EntityNode from "./EntityNode.svelte";
    import GroupNode from "./GroupNode.svelte";
    import CustomEdge from "./CustomEdge.svelte";
    import EntityCreationWizard from "./EntityCreationWizard.svelte";
    import EventFilterBanner from "./EventFilterBanner.svelte";
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
        filteredEntityIds = null,
        filterEventText = null,
    }: {
        guidanceConfig: GuidanceConfig;
        lineageEnabled?: boolean;
        exposuresEnabled?: boolean;
        hasExposuresData?: boolean;
        filteredEntityIds?: string[] | null;
        filterEventText?: string | null;
    } = $props();

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

    // Entity filtering logic
    // Filter nodes to show only entities with IDs in filteredEntityIds
    const filteredNodes = $derived(() => {
        if (!filteredEntityIds || filteredEntityIds.length === 0) {
            return $nodes;
        }

        // Filter out entity IDs that don't exist in $nodes (handle deleted entities)
        // Keep group nodes visible to maintain canvas structure
        return $nodes.filter(node =>
            node.type === 'group' || filteredEntityIds.includes(node.id)
        );
    });

    // Create a reactive local nodes variable for binding
    // This syncs with either filtered or all nodes based on filter state
    let displayNodes = $state<Node[]>([]);

    // Sync filtered nodes to displayNodes
    $effect(() => {
        displayNodes = filteredNodes();
    });


    // Sync changes from displayNodes back to $nodes store when users interact
    // This ensures drag operations and other changes are persisted
    $effect(() => {
        if (filteredEntityIds && filteredEntityIds.length > 0) {
            let updatedCount = 0;
            let missingCount = 0;
            const updatedIds: string[] = [];
            // In filtered mode, update the corresponding nodes in the store
            displayNodes.forEach(displayNode => {
                const storeNodeIndex = $nodes.findIndex(n => n.id === displayNode.id);
                if (storeNodeIndex >= 0 && $nodes[storeNodeIndex] !== displayNode) {
                    $nodes[storeNodeIndex] = displayNode;
                    updatedCount += 1;
                    if (updatedIds.length < 5) {
                        updatedIds.push(displayNode.id);
                    }
                } else if (storeNodeIndex < 0) {
                    missingCount += 1;
                }
            });
            if (updatedCount > 0) {
                // Force store update so autosave reacts in filtered mode.
                $nodes = [...$nodes];
            }
        } else {
            // In non-filtered mode, sync displayNodes directly to $nodes store
            // This ensures edges update during drag operations
            $nodes = displayNodes;
        }
    });

    // Filter edges to only show connections between filtered entities
    const displayEdges = $derived(() => {
        if (!filteredEntityIds || filteredEntityIds.length === 0) {
            return $edges;
        }

        // Get set of visible node IDs for efficient lookup
        const visibleNodeIds = new Set(displayNodes.map(n => n.id));

        // Only show edges where both source and target are visible
        return $edges
            .filter(edge =>
            visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
            )
            .map(edge => ({
                ...edge,
                data: {
                    ...(edge.data || {}),
                    layout: "straight",
                },
            }));
    });

    // Calculate filtered entity count (exclude group nodes)
    const filteredEntityCount = $derived(() => {
        if (!filteredEntityIds || filteredEntityIds.length === 0) {
            return 0;
        }
        return displayNodes.filter(node => node.type === 'entity').length;
    });

    // Detect if all filtered entities have been deleted
    const allFilteredEntitiesDeleted = $derived(() => {
        return filteredEntityIds && filteredEntityIds.length > 0 && filteredEntityCount() === 0;
    });

    // Clear filter handler - navigates back to canvas without URL params
    function handleClearFilter() {
        goto('/canvas');
    }

    // Wizard state
    let wizardOpen = $state(false);
    let wizardData = $state<EntityWizardData | null>(null);

    // Position calculator services
    const positioner = new DimensionalModelPositioner();
    const groupSizeCalculator = new GroupSizeCalculator();

    const isEventFiltered = $derived(
        !!filteredEntityIds && filteredEntityIds.length > 0
    );

    function getNodeSize(node: Node): { width: number; height: number } {
        const width =
            (node.measured?.width as number | undefined) ??
            (node.data?.width as number | undefined) ??
            280;
        const height =
            (node.measured?.height as number | undefined) ??
            (node.data?.panelHeight as number | undefined) ??
            (node.data?.height as number | undefined) ??
            220;
        return { width, height };
    }

    function applyStarSchemaLayout(nodesToLayout: Node[]): Node[] {
        const entityNodes = nodesToLayout.filter((node) => node.type === "entity");
        if (entityNodes.length === 0) {
            return nodesToLayout;
        }

        const factNodes = entityNodes.filter(
            (node) => node.data?.entity_type === "fact",
        );
        const dimensionNodes = entityNodes.filter(
            (node) => node.data?.entity_type !== "fact",
        );

        const center = positioner.calculateCenter([]);

        const factSizes = factNodes.map(getNodeSize);
        const dimSizes = dimensionNodes.map(getNodeSize);
        const maxFactWidth = Math.max(...factSizes.map((s) => s.width), 0);
        const maxDimWidth = Math.max(...dimSizes.map((s) => s.width), 0);
        const maxDimHeight = Math.max(...dimSizes.map((s) => s.height), 0);

        const dimCount = dimensionNodes.length;
        const minSpacing = Math.max(maxDimWidth, maxDimHeight) + 140;
        const ringRadiusFromCount =
            dimCount > 0 ? (dimCount * minSpacing) / (2 * Math.PI) : 0;
        const ringRadiusFromFacts =
            (maxFactWidth / 2) + (maxDimWidth / 2) + 200;
        const dimensionRingRadius = Math.max(380, ringRadiusFromCount, ringRadiusFromFacts);

        const factRingRadius = factNodes.length > 1 ? 140 : 0;

        const positioned = new Map<string, { x: number; y: number }>();

        factNodes.forEach((node, index) => {
            const size = getNodeSize(node);
            const angle =
                factNodes.length > 1
                    ? (index / factNodes.length) * Math.PI * 2
                    : 0;
            const x = center.x + Math.cos(angle) * factRingRadius - size.width / 2;
            const y = center.y + Math.sin(angle) * factRingRadius - size.height / 2;
            positioned.set(node.id, { x, y });
        });

        dimensionNodes.forEach((node, index) => {
            const size = getNodeSize(node);
            const angle =
                dimCount > 0
                    ? (index / dimCount) * Math.PI * 2 - Math.PI / 2
                    : 0;
            const x = center.x + Math.cos(angle) * dimensionRingRadius - size.width / 2;
            const y = center.y + Math.sin(angle) * dimensionRingRadius - size.height / 2;
            positioned.set(node.id, { x, y });
        });

        return nodesToLayout.map((node) => {
            const nextPosition = positioned.get(node.id);
            if (!nextPosition) {
                return node;
            }
            return {
                ...node,
                position: nextPosition,
            };
        });
    }

    let lastLayoutKey = $state<string | null>(null);

    $effect(() => {
        if (!isEventFiltered) {
            lastLayoutKey = null;
            return;
        }

        if (isDragging) {
            return;
        }

        const key = `${filterEventText ?? ""}::${filteredEntityIds?.slice().sort().join(",") ?? ""}`;
        if (lastLayoutKey === key) {
            return;
        }

        lastLayoutKey = key;
        displayNodes = applyStarSchemaLayout(displayNodes);
    });

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
        console.log("Drag start:", params.targetNode?.id);
        isDragging = true;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    function onNodeDragStop(params: any) {
        console.log("Drag stop:", params.targetNode?.id);
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
        bind:nodes={displayNodes}
        edges={displayEdges()}
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

        {#if allFilteredEntitiesDeleted()}
            <div
                class="absolute inset-0 flex items-center justify-center pointer-events-none z-10"
            >
                <div
                    class="bg-white/90 backdrop-blur-sm p-8 rounded-xl border border-slate-200 shadow-xl text-center max-w-md mx-4"
                >
                    <div
                        class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4"
                    >
                        <Icon
                            icon="lucide:filter-x"
                            class="w-8 h-8 text-blue-600"
                        />
                    </div>
                    <h3 class="text-xl font-bold text-slate-800 mb-2">
                        No Entities Found
                    </h3>
                    <p class="text-slate-600 mb-6">
                        All entities from the filtered business event have been deleted or are no longer available.
                    </p>
                    <button
                        class="bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 font-medium transition-colors shadow-md pointer-events-auto flex items-center justify-center gap-2 mx-auto"
                        onclick={handleClearFilter}
                    >
                        <Icon icon="lucide:x" class="w-4 h-4" />
                        Clear Filter and View All Entities
                    </button>
                </div>
            </div>
        {:else if $nodes.length === 0}
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

    <!-- Event Filter Banner - Show when filtering by business event -->
    {#if filteredEntityIds && filteredEntityIds.length > 0 && filterEventText}
        <EventFilterBanner
            eventText={filterEventText}
            entityCount={filteredEntityCount()}
            onClear={handleClearFilter}
        />
    {/if}

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
        modelingStyle={$modelingStyle}
    />
</div>
