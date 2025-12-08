<script lang="ts">
    import { onMount, untrack } from "svelte";
    import {
        nodes,
        edges,
        dbtModels,
        viewMode,
        configStatus,
        initHistory,
        pushHistory,
        undo,
        redo,
        canUndo,
        canRedo,
        folderFilter,
        tagFilter,
        groupByFolder,
    } from "$lib/stores";
    import {
        getManifest,
        getDataModel,
        saveDataModel,
        getConfigStatus,
        getConfigInfo,
        inferRelationships,
        syncDbtTests,
    } from "$lib/api";
    import { getParallelOffset, getModelFolder } from "$lib/utils";
    import { applyDagreLayout } from "$lib/layout";
    import Sidebar from "$lib/components/Sidebar.svelte";
    import Canvas from "$lib/components/Canvas.svelte";
    import ConfigInfoModal from "$lib/components/ConfigInfoModal.svelte";
    import { type Node, type Edge } from "@xyflow/svelte";
    import type { ConfigInfo, DbtModel } from "$lib/types";
    import Icon from "@iconify/svelte";
    import logoHref from "$lib/assets/trellis_squared.svg?url";

    let loading = $state(true);
    let saving = $state(false);
    let syncing = $state(false);
    let syncMessage = $state<string | null>(null);
    let lastSavedState = "";
    let showConfigInfoModal = $state(false);
    let configInfoLoading = $state(false);
    let configInfoError = $state<string | null>(null);
    let configInfo = $state<ConfigInfo | null>(null);

    async function handleSyncDbt() {
        syncing = true;
        syncMessage = null;
        try {
            const result = await syncDbtTests();
            syncMessage = `✓ ${result.message}`;
            setTimeout(() => {
                syncMessage = null;
            }, 3000);
        } catch (e) {
            syncMessage = `✗ ${e instanceof Error ? e.message : "Sync failed"}`;
            setTimeout(() => {
                syncMessage = null;
            }, 5000);
        } finally {
            syncing = false;
        }
    }

    async function handleOpenConfigInfo() {
        showConfigInfoModal = true;
        configInfoLoading = true;
        configInfoError = null;
        try {
            const info = await getConfigInfo();
            if (!info) {
                configInfoError = "Unable to fetch config info";
            } else {
                configInfo = info;
            }
        } catch (e) {
            console.error(e);
            configInfoError = "Unable to fetch config info";
        } finally {
            configInfoLoading = false;
        }
    }

    async function handleInferFromDbt() {
        syncing = true;
        syncMessage = "Inferring...";
        try {
            const inferred = await inferRelationships();
            if (inferred.length > 0) {
                let addedCount = 0;
                let addedNodes = 0;
                const newEdges = [...$edges];
                const existingEntityIds = new Set(
                    $nodes.filter((n) => n.type === "entity").map((n) => n.id),
                );

                function maybeAddEntity(id: string | undefined | null) {
                    if (!id) return;
                    if (existingEntityIds.has(id)) return;

                    const model =
                        $dbtModels.find(
                            (m) => m.unique_id === id || m.name === id,
                        ) ?? null;
                    const folder = model ? getModelFolder(model) : null;

                    const newNode: Node = {
                        id,
                        type: "entity",
                        position: { x: 200 + addedNodes * 60, y: 200 },
                        zIndex: 10,
                        data: {
                            label: model?.name ?? id,
                            description: model?.description ?? "",
                            dbt_model: model?.unique_id ?? null,
                            additional_models: model?.alias ? [model.alias] : [],
                            drafted_fields: [],
                            width: 280,
                            panelHeight: 200,
                            collapsed: false,
                            folder,
                            tags: model?.tags ?? [],
                        },
                    };

                    $nodes = [...$nodes, newNode];
                    existingEntityIds.add(id);
                    addedNodes += 1;
                }

                inferred.forEach((r: any) => {
                    maybeAddEntity(r.source);
                    maybeAddEntity(r.target);

                    const exists = newEdges.some(
                        (e) =>
                            e.source === r.source &&
                            e.target === r.target &&
                            e.data?.source_field === r.source_field &&
                            e.data?.target_field === r.target_field,
                    );

                    if (!exists) {
                        const parallelEdges = newEdges.filter(
                            (e) =>
                                (e.source === r.source &&
                                    e.target === r.target) ||
                                (e.source === r.target &&
                                    e.target === r.source),
                        );
                        const currentCount = parallelEdges.length;

                        const baseId = `e${r.source}-${r.target}`;
                        const edgeId = `${baseId}-${Date.now()}-${currentCount}`;

                        newEdges.push({
                            id: edgeId,
                            source: r.source,
                            target: r.target,
                            type: "custom",
                            data: {
                                label: r.label || "",
                                type: r.type || "one_to_many",
                                source_field: r.source_field,
                                target_field: r.target_field,
                                label_dx: r.label_dx || 0,
                                label_dy: r.label_dy || 0,
                                parallelOffset: getParallelOffset(currentCount),
                            },
                        });
                        addedCount++;
                    }
                });

                if (addedCount > 0) {
                    $edges = newEdges;
                    syncMessage = `✓ Added ${addedCount} new${addedNodes ? `, ${addedNodes} nodes` : ""}`;
                    setTimeout(() => {
                        syncMessage = null;
                    }, 3000);
                } else if (addedNodes > 0) {
                    syncMessage = `✓ Added ${addedNodes} nodes`;
                    setTimeout(() => {
                        syncMessage = null;
                    }, 3000);
                } else {
                    syncMessage = "No new found";
                    setTimeout(() => {
                        syncMessage = null;
                    }, 3000);
                }
            } else {
                syncMessage = "No relationships in dbt";
                setTimeout(() => {
                    syncMessage = null;
                }, 3000);
            }
        } catch (e) {
            console.error(e);
            syncMessage = "✗ Failed to infer";
            setTimeout(() => {
                syncMessage = null;
            }, 5000);
        } finally {
            syncing = false;
        }
    }

    async function handleAutoLayout() {
        if (loading) return;
        
        const entityNodes = $nodes.filter((n) => n.type === "entity");
        if (entityNodes.length === 0) return;

        const layoutedNodes = await applyDagreLayout($nodes, $edges);
        $nodes = layoutedNodes;
        // fitView prop on Canvas will automatically adjust the view
    }
    let sidebarWidth = $state(280);
    let resizingSidebar = $state(false);
    let resizeStartX = 0;
    let resizeStartWidth = 0;
    const MIN_SIDEBAR = 200;
    const MAX_SIDEBAR = 420;

    function onSidebarPointerMove(event: PointerEvent) {
        if (!resizingSidebar) return;
        const delta = event.clientX - resizeStartX;
        sidebarWidth = Math.min(
            MAX_SIDEBAR,
            Math.max(MIN_SIDEBAR, resizeStartWidth + delta),
        );
    }

    function stopSidebarResize() {
        if (!resizingSidebar) return;
        resizingSidebar = false;
        window.removeEventListener("pointermove", onSidebarPointerMove);
        window.removeEventListener("pointerup", stopSidebarResize);
    }

    function startSidebarResize(event: PointerEvent) {
        event.preventDefault();
        resizingSidebar = true;
        resizeStartX = event.clientX;
        resizeStartWidth = sidebarWidth;
        window.addEventListener("pointermove", onSidebarPointerMove);
        window.addEventListener("pointerup", stopSidebarResize, { once: true });
    }

    onMount(() => {
        (async () => {
            console.log(`[${Date.now()}] Page mounted, loading data...`);
            try {
                // Check Config Status
                const status = await getConfigStatus();
                $configStatus = status;

                // Load Manifest
                const models = await getManifest();
                $dbtModels = models;

                // Load Data Model
                const dataModel = await getDataModel();

                // If no relationships in data model, try to infer from dbt yml files
                let relationships = dataModel.relationships || [];
                if (relationships.length === 0) {
                    console.log(
                        "No relationships found in data model, attempting to infer from dbt yml files...",
                    );
                    const inferred = await inferRelationships();
                    if (inferred.length > 0) {
                        relationships = inferred;
                        console.log(
                            `Inferred ${inferred.length} relationships from dbt yml files`,
                        );
                    }
                }

                // Helper to get folder and tags from dbt model
                function getEntityMetadata(entity: any) {
                    if (!entity.dbt_model) return { folder: null };

                    const model = models.find(
                        (m: any) => m.unique_id === entity.dbt_model,
                    );
                    if (!model) return { folder: null };

                    return { folder: getModelFolder(model) };
                }

                // Map data model to Svelte Flow format with metadata
                const entityNodes = (dataModel.entities || []).map((e: any) => {
                    const metadata = getEntityMetadata(e);
                    // Use tags from entity data if present, otherwise empty array
                    const entityTags = e.tags || [];
                    return {
                        id: e.id,
                        type: "entity",
                        position: e.position || { x: 0, y: 0 },
                        zIndex: 10, // Entities should be above groups (zIndex 1)
                        data: {
                            label: e.label,
                            description: e.description,
                            dbt_model: e.dbt_model,
                            additional_models: e.additional_models,
                            drafted_fields: e.drafted_fields,
                            width: e.width ?? 280,
                            panelHeight: e.panel_height ?? e.panelHeight ?? 200,
                            collapsed: e.collapsed ?? false,
                            folder: metadata.folder,
                            tags: entityTags,
                        },
                        parentId: undefined, // Will be set if grouping is enabled
                    };
                });

                // Create group nodes if grouping is enabled
                const groupNodes: Node[] = [];
                if ($groupByFolder) {
                    const folderMap = new Map<string, any[]>();

                    entityNodes.forEach((node: any) => {
                        if (node.data.folder) {
                            if (!folderMap.has(node.data.folder)) {
                                folderMap.set(node.data.folder, []);
                            }
                            folderMap.get(node.data.folder)!.push(node);
                        }
                    });

                    // Create group nodes for each folder
                    const PADDING = 40;
                    const HEADER_HEIGHT = 60;
                    const GROUP_SPACING = 50; // Minimum spacing between groups

                    const tempGroups: Array<{
                        x: number;
                        y: number;
                        width: number;
                        height: number;
                        node: any;
                    }> = [];

                    folderMap.forEach((children, folderPath) => {
                        if (children.length === 0) return;

                        const groupId = `group-${folderPath.replace(/\//g, "-")}`;

                        // Calculate bounding box of children
                        const minX = Math.min(
                            ...children.map((n) => n.position.x),
                        );
                        const minY = Math.min(
                            ...children.map((n) => n.position.y),
                        );
                        const maxX = Math.max(
                            ...children.map(
                                (n) => n.position.x + (n.data.width || 280),
                            ),
                        );
                        const maxY = Math.max(
                            ...children.map(
                                (n) =>
                                    n.position.y + (n.data.panelHeight || 200),
                            ),
                        );

                        let groupX = minX - PADDING;
                        let groupY = minY - PADDING - HEADER_HEIGHT;
                        const groupWidth = maxX - minX + PADDING * 2;
                        const groupHeight =
                            maxY - minY + PADDING * 2 + HEADER_HEIGHT;

                        // Check for overlaps with existing groups and adjust position
                        for (const existing of tempGroups) {
                            const overlapX =
                                groupX <
                                    existing.x +
                                        existing.width +
                                        GROUP_SPACING &&
                                groupX + groupWidth + GROUP_SPACING >
                                    existing.x;
                            const overlapY =
                                groupY <
                                    existing.y +
                                        existing.height +
                                        GROUP_SPACING &&
                                groupY + groupHeight + GROUP_SPACING >
                                    existing.y;

                            if (overlapX && overlapY) {
                                // Move this group to the right of the overlapping group
                                groupX =
                                    existing.x + existing.width + GROUP_SPACING;
                                // If still overlapping vertically, move down
                                if (
                                    groupY <
                                    existing.y + existing.height + GROUP_SPACING
                                ) {
                                    groupY =
                                        existing.y +
                                        existing.height +
                                        GROUP_SPACING;
                                }
                            }
                        }

                        const groupNode = {
                            id: groupId,
                            type: "group",
                            position: { x: groupX, y: groupY },
                            style: `width: ${groupWidth}px; height: ${groupHeight}px;`,
                            zIndex: 1, // Groups should be behind entities
                            data: {
                                label:
                                    folderPath.split("/").pop() || folderPath,
                                description: `Folder: ${folderPath}`,
                                width: groupWidth,
                                height: groupHeight,
                                collapsed: false,
                            },
                        };

                        tempGroups.push({
                            x: groupX,
                            y: groupY,
                            width: groupWidth,
                            height: groupHeight,
                            node: groupNode,
                        });
                        groupNodes.push(groupNode);

                        // Convert children to relative positions and set parent
                        children.forEach((child: any) => {
                            child.parentId = groupId;
                            child.position = {
                                x: child.position.x - groupX,
                                y: child.position.y - groupY,
                            };
                            // Mark as extent parent so it stays within bounds
                            child.extent = "parent";
                        });
                    });
                }

                $nodes = [...groupNodes, ...entityNodes] as Node[];

                const edgeCounts = new Map<string, number>();
                $edges = relationships.map((r: any) => {
                    const pairKey =
                        r.source < r.target
                            ? `${r.source}-${r.target}`
                            : `${r.target}-${r.source}`;
                    const currentCount = edgeCounts.get(pairKey) ?? 0;
                    edgeCounts.set(pairKey, currentCount + 1);

                    const baseId = `e${r.source}-${r.target}`;
                    let edgeId = `${baseId}-${currentCount}`;
                    if (currentCount === 0) edgeId = baseId;

                    return {
                        id: edgeId,
                        source: r.source,
                        target: r.target,
                        type: "custom",
                        data: {
                            label: r.label || "",
                            type: r.type || "one_to_many",
                            source_field: r.source_field,
                            target_field: r.target_field,
                            label_dx: r.label_dx || 0,
                            label_dy: r.label_dy || 0,
                            parallelOffset: getParallelOffset(currentCount),
                        },
                    };
                }) as Edge[];

                // Deduplicate edges on load to clean up any existing bad state
                const uniqueEdges = new Map<string, Edge>();
                $edges.forEach((edge) => {
                    // Create a unique key based on content, ignoring ID
                    // Key: source|target|source_field|target_field
                    // We sort source/target to handle bidirectional duplicates if any (though usually direction matters)
                    // But for now let's stick to exact direction match unless it's a generic relationship
                    const key = `${edge.source}|${edge.target}|${edge.data?.source_field || ""}|${edge.data?.target_field || ""}`;

                    if (!uniqueEdges.has(key)) {
                        uniqueEdges.set(key, edge);
                    } else {
                        console.warn(
                            `Removed duplicate edge on load: ${edge.id} (duplicate of ${uniqueEdges.get(key)?.id})`,
                        );
                    }
                });
                $edges = Array.from(uniqueEdges.values());

                // Auto-apply layout if all entity nodes are at default position (no saved layout)
                const layoutCheckNodes = $nodes.filter((n) => n.type === "entity");
                if (layoutCheckNodes.length > 0) {
                    const allAtDefaultPosition = layoutCheckNodes.every(
                        (n) => n.position.x === 0 && n.position.y === 0,
                    );
                    
                    if (allAtDefaultPosition) {
                        console.log("No saved positions found, applying auto-layout...");
                        $nodes = await applyDagreLayout($nodes, $edges);
                    }
                }

                lastSavedState = JSON.stringify({
                    nodes: $nodes,
                    edges: $edges,
                });
                initHistory();
            } catch (e) {
                console.error("Initialization error:", e);
                alert("Failed to initialize. Check backend connection.");
            } finally {
                loading = false;
            }
        })();

        // Keyboard shortcut for undo/redo
        function handleKeydown(e: KeyboardEvent) {
            if ((e.metaKey || e.ctrlKey) && e.key === "z") {
                e.preventDefault();
                if (e.shiftKey) {
                    redo();
                } else {
                    undo();
                }
            }
            // Ctrl+Y as alternative redo
            if ((e.metaKey || e.ctrlKey) && e.key === "y") {
                e.preventDefault();
                redo();
            }
        }
        window.addEventListener("keydown", handleKeydown);
        return () => window.removeEventListener("keydown", handleKeydown);
    });

    // Auto-save logic
    let timeout: ReturnType<typeof setTimeout>;

    $effect(() => {
        if (loading) return;

        // Track dependencies
        const currentNodes = $nodes;
        const currentEdges = $edges;

        console.log("State changed:", {
            nodes: currentNodes.length,
            edges: currentEdges.length,
        });

        const state = JSON.stringify({
            nodes: currentNodes,
            edges: currentEdges,
        });
        if (state === lastSavedState) return;

        // Push to undo history
        pushHistory();

        clearTimeout(timeout);
        saving = true;
        timeout = setTimeout(async () => {
            try {
                // Convert back to data model format
                const dataModel = {
                    version: 0.1,
                    entities: currentNodes
                        .filter((n) => n.type === "entity") // Only save entity nodes, not group nodes
                        .map((n) => ({
                            id: n.id,
                            label: n.data.label as string,
                            description: n.data.description as string | undefined,
                            dbt_model: n.data.dbt_model as string | undefined,
                            additional_models: n.data?.additional_models as string[] | undefined,
                            drafted_fields: n.data?.drafted_fields as any[] | undefined,
                            position: n.position,
                            width: n.data?.width as number | undefined,
                            panel_height: n.data?.panelHeight as number | undefined,
                            collapsed: (n.data?.collapsed as boolean) ?? false,
                            tags: (n.data?.tags as string[]) || [],
                        })),
                    relationships: currentEdges.map((e) => ({
                        source: e.source,
                        target: e.target,
                        label: (e.data?.label as string) || "",
                        type: (e.data?.type as 'one_to_many' | 'many_to_one' | 'one_to_one' | 'many_to_many') || "one_to_many",
                        source_field: e.data?.source_field as string | undefined,
                        target_field: e.data?.target_field as string | undefined,
                        label_dx: e.data?.label_dx as number | undefined,
                        label_dy: e.data?.label_dy as number | undefined,
                    })),
                };

                await saveDataModel(dataModel);
                lastSavedState = state;
            } catch (e) {
                console.error("Save failed", e);
            } finally {
                saving = false;
            }
        }, 1000); // 1s debounce
    });

    // Apply filters to node visibility
    $effect(() => {
        if (loading) return;

        const activeFolder = $folderFilter;
        const activeTags = $tagFilter;
        const models = $dbtModels; // Dependency on dbtModels

        // Use untrack to read current nodes and edges without creating dependency
        const currentNodes = untrack(() => $nodes);
        const currentEdges = untrack(() => $edges);

        // Build updated nodes array
        const updatedNodes = currentNodes.map((node) => {
            // Skip group nodes
            if (node.type === "group") {
                return node;
            }

            // Find all associated models (primary + additional)
            const primaryModel = models.find(
                (m) => m.unique_id === node.data.dbt_model,
            );
            const additionalModelIds = (node.data?.additional_models as string[]) || [];
            const additionalModels = additionalModelIds
                .map((id) => models.find((m) => m.unique_id === id))
                .filter((m): m is DbtModel => m !== undefined);
            const allBoundModels = primaryModel
                ? [primaryModel, ...additionalModels]
                : additionalModels;

            // Check if node matches filters
            let visible = true;

            if (activeFolder.length > 0) {
                if (allBoundModels.length === 0) {
                    visible = false;
                } else {
                    // Entity is visible if ANY bound model matches the folder filter
                    const matchingFolders = allBoundModels
                        .map((m) => getModelFolder(m))
                        .filter((f): f is string => f !== null);
                    visible =
                        visible &&
                        matchingFolders.some((folder) =>
                            activeFolder.includes(folder),
                        );
                }
            }

            if (activeTags.length > 0) {
                // Combine tags from all bound models (manifest) and entity data (user-added)
                const allModelTags = allBoundModels.flatMap((m) => m.tags || []);
                const entityTags = (node.data?.tags as string[]) || [];
                const nodeTags = [...new Set([...allModelTags, ...entityTags])];
                
                visible =
                    visible &&
                    nodeTags.length > 0 &&
                    activeTags.some((tag) => nodeTags.includes(tag));
            }

            // Return updated node with hidden property
            return {
                ...node,
                hidden: !visible,
            };
        });

        // Create a map of node visibility for quick lookup
        const nodeVisibility = new Map<string, boolean>();
        updatedNodes.forEach((node) => {
            nodeVisibility.set(node.id, !node.hidden);
        });

        // Hide edges where either source or target node is hidden
        const updatedEdges = currentEdges.map((edge) => {
            const sourceVisible = nodeVisibility.get(edge.source) ?? true;
            const targetVisible = nodeVisibility.get(edge.target) ?? true;

            return {
                ...edge,
                hidden: !sourceVisible || !targetVisible,
            };
        });

        // Update the stores
        $nodes = updatedNodes;
        $edges = updatedEdges;
    });
</script>

<div
    class="flex flex-col h-screen overflow-hidden font-sans text-gray-900 bg-gray-50"
>
    <!-- Header -->
    <header
        class="h-16 bg-white border-b border-gray-200 flex items-center px-6 justify-between z-20 shadow-sm shrink-0"
    >
        <!-- Brand -->
        <div class="flex items-center gap-3">
            <img
                src={logoHref}
                alt="trellis logo"
                class="w-8 h-8 rounded-lg shadow-sm"
            />
            <div class="flex flex-col">
                <h1
                    class="font-bold text-lg text-gray-900 leading-tight tracking-tight"
                >
                    trellis
                </h1>
                <span
                    class="text-[10px] text-gray-500 font-medium tracking-wider uppercase"
                    >Data Model UI</span
                >
            </div>

            {#if saving}
                <span class="text-xs text-gray-400 animate-pulse ml-2"
                    >Saving...</span
                >
            {/if}
            {#if loading}
                <span class="text-xs text-primary-500 ml-2">Loading...</span>
            {/if}
        </div>

        <!-- View Switcher -->
        <div
            class="flex bg-gray-100 rounded-lg p-1 border border-gray-200/60"
        >
            <button
                class="px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center gap-2"
                class:bg-white={$viewMode === "conceptual"}
                class:text-primary-600={$viewMode === "conceptual"}
                class:shadow-sm={$viewMode === "conceptual"}
                class:text-gray-500={$viewMode !== "conceptual"}
                class:hover:text-gray-900={$viewMode !== "conceptual"}
                onclick={() => ($viewMode = "conceptual")}
            >
                <Icon icon="octicon:workflow-16" class="w-4 h-4" />
                Conceptual
            </button>
            <button
                class="px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center gap-2"
                class:bg-white={$viewMode === "logical"}
                class:text-primary-600={$viewMode === "logical"}
                class:shadow-sm={$viewMode === "logical"}
                class:text-gray-500={$viewMode !== "logical"}
                class:hover:text-gray-900={$viewMode !== "logical"}
                onclick={() => ($viewMode = "logical")}
            >
                <Icon icon="lucide:database" class="w-4 h-4" />
                Logical
            </button>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-3">
            {#if syncMessage}
                <div
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-50 border border-gray-200"
                >
                    {#if syncMessage.startsWith("✓")}
                        <div class="w-2 h-2 rounded-full bg-success-500"></div>
                        <span class="text-xs font-medium text-success-700"
                            >{syncMessage.substring(2)}</span
                        >
                    {:else if syncMessage.startsWith("✗")}
                        <div class="w-2 h-2 rounded-full bg-danger-500"></div>
                        <span class="text-xs font-medium text-danger-700"
                            >{syncMessage.substring(2)}</span
                        >
                    {:else}
                        <span class="text-xs text-gray-600">{syncMessage}</span
                        >
                    {/if}
                </div>
            {/if}

            <div class="h-6 w-px bg-gray-200 mx-1"></div>

            <button
                onclick={handleOpenConfigInfo}
                class="px-4 py-2 text-sm rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-2 shadow-sm"
                title="Show resolved config paths"
            >
                <Icon icon="lucide:info" class="w-4 h-4" />
                Config info
            </button>

            <button
                onclick={handleAutoLayout}
                disabled={loading}
                class="px-4 py-2 text-sm rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
                title="Automatically arrange entities and relationships for optimal readability"
            >
                <Icon icon="lucide:layout-grid" class="w-4 h-4" />
                Auto Layout
            </button>

            <button
                onclick={handleInferFromDbt}
                disabled={syncing || loading}
                class="px-4 py-2 text-sm rounded-lg font-medium text-white bg-primary-600 border border-transparent hover:bg-primary-50 hover:text-primary-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
                title="Import relationship tests from dbt yml files"
            >
                <Icon icon="lucide:download" class="w-4 h-4" />
                Pull from dbt
            </button>

            <button
                onclick={handleSyncDbt}
                disabled={syncing || loading}
                class="px-4 py-2 text-sm rounded-lg font-medium text-white bg-primary-600 border border-transparent hover:bg-primary-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
                title="Sync entity & field-definitions and relationship-tests to dbt schema.yml files"
            >
                {#if syncing}
                    <Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
                {:else}
                    <Icon icon="lucide:upload" class="w-4 h-4" />
                {/if}
                Push to dbt
            </button>
        </div>
    </header>

    <main class="flex-1 flex overflow-hidden relative">
        <Sidebar width={sidebarWidth} {loading} />
        <div
            class="resize-handle h-full"
            class:active={resizingSidebar}
            onpointerdown={startSidebarResize}
        ></div>
        <Canvas />
    </main>

    <ConfigInfoModal
        open={showConfigInfoModal}
        info={configInfo}
        loading={configInfoLoading}
        error={configInfoError}
        onClose={() => (showConfigInfoModal = false)}
        onRetry={handleOpenConfigInfo}
    />
</div>

<style>
    .resize-handle {
        width: 8px;
        height: 100%;
        cursor: col-resize;
        background: transparent;
        transition: background 0.2s ease;
        pointer-events: auto;
        touch-action: none;
        flex-shrink: 0;
        position: relative;
        z-index: 10;
    }

    .resize-handle:hover,
    .resize-handle.active {
        background: rgba(148, 163, 184, 0.8);
    }
</style>
