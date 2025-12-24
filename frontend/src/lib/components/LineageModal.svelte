<script lang="ts">
    import {
        SvelteFlow,
        Controls,
        Background,
        BackgroundVariant,
        MiniMap,
        type Node,
        type Edge,
    } from "@xyflow/svelte";
    import { getLineage } from "$lib/api";
    import type { LineageResponse, LineageNode, LineageEdge } from "$lib/types";
    import Icon from "@iconify/svelte";
    import LineageSourceNode from "./LineageSourceNode.svelte";
    import LineageModelNode from "./LineageModelNode.svelte";

    const { open = false, modelId = null, onClose } = $props<{
        open: boolean;
        modelId: string | null;
        onClose: () => void;
    }>();

    let loading = $state(false);
    let error = $state<string | null>(null);
    let lineageData = $state<LineageResponse | null>(null);
    let lineageNodes = $state<Node[]>([]);
    let lineageEdges = $state<Edge[]>([]);

    const nodeTypes = {
        source: LineageSourceNode,
        default: LineageModelNode, // Use custom node type for regular models
    };

    // Progressive display state - show all levels initially, but can collapse later
    let expandedLevels = $state<Set<number>>(new Set());
    let placeholderNodes = $state<Map<string, { parentId: string; level: number }>>(new Map());

    // Fetch lineage when modal opens
    $effect(() => {
        if (open && modelId) {
            loadLineage();
        } else {
            // Reset state when modal closes
            lineageData = null;
            lineageNodes = [];
            lineageEdges = [];
            error = null;
            expandedLevels = new Set();
            placeholderNodes = new Map();
        }
    });

    async function loadLineage() {
        if (!modelId) return;

        loading = true;
        error = null;

        try {
            const data = await getLineage(modelId);
            if (!data) {
                error = "Model not found or lineage could not be generated.";
                return;
            }

            lineageData = data;
            updateGraphDisplay();
        } catch (e) {
            console.error("Error loading lineage:", e);
            error = e instanceof Error ? e.message : "Failed to load lineage";
        } finally {
            loading = false;
        }
    }

    function updateGraphDisplay() {
        if (!lineageData) return;

        // Filter nodes based on expanded levels and progressive display
        const visibleNodes: Node[] = [];
        const visibleEdges: Edge[] = [];
        const newPlaceholderNodes = new Map<string, { parentId: string; level: number }>();

        // Bucket nodes by level to spread siblings horizontally
        const levelBuckets = new Map<number, LineageNode[]>();
        for (const node of lineageData.nodes) {
            const bucket = levelBuckets.get(node.level) ?? [];
            bucket.push(node);
            levelBuckets.set(node.level, bucket);
        }

        // Precompute each node's sibling index and total at its level
        const levelPositions = new Map<string, { index: number; count: number }>();
        for (const [, nodes] of levelBuckets) {
            const count = nodes.length;
            nodes.forEach((n, idx) => levelPositions.set(n.id, { index: idx, count }));
        }

        // Process nodes - show all nodes initially (no progressive filtering for now)
        // Sources should always be visible
        for (const node of lineageData.nodes) {
            const pos = levelPositions.get(node.id);
            const indexInLevel = pos?.index ?? 0;
            const countAtLevel = pos?.count ?? 1;

            // Always show sources, root, and direct dependencies
            if (node.isSource || node.level === 0 || node.level === 1) {
                visibleNodes.push(createFlowNode(node, indexInLevel, countAtLevel));
            } else if (expandedLevels.size === 0 || expandedLevels.has(node.level)) {
                // Show if no filtering or if level is expanded
                visibleNodes.push(createFlowNode(node, indexInLevel, countAtLevel));
            }
        }

        // Process edges - only show edges between visible nodes
        const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
        for (const edge of lineageData.edges) {
            if (visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)) {
                visibleEdges.push({
                    id: `edge-${edge.source}-${edge.target}`,
                    source: edge.source,
                    target: edge.target,
                    type: "default",
                });
            }
        }

        // Create placeholder nodes for collapsed sections
        for (const node of lineageData.nodes) {
            const level = node.level;
            if (level > 1 && !expandedLevels.has(level)) {
                // Check if this node has upstream dependencies
                const hasUpstream = lineageData.edges.some((e) => e.target === node.id);
                if (hasUpstream) {
                    // Find parent node
                    const parentEdge = lineageData.edges.find((e) => e.target === node.id);
                    if (parentEdge) {
                        const placeholderId = `placeholder-${parentEdge.source}-${level}`;
                        if (!newPlaceholderNodes.has(placeholderId)) {
                            newPlaceholderNodes.set(placeholderId, {
                                parentId: parentEdge.source,
                                level: level,
                            });
                        }
                    }
                }
            }
        }

        // Add placeholder nodes
        for (const [placeholderId, info] of newPlaceholderNodes) {
            const parentNode = visibleNodes.find((n) => n.id === info.parentId);
            if (parentNode) {
                visibleNodes.push({
                    id: placeholderId,
                    type: "placeholder",
                    position: {
                        x: parentNode.position.x,
                        y: parentNode.position.y + 60,
                    },
                    data: {
                        label: "...",
                        level: info.level,
                        parentId: info.parentId,
                        onClick: () => expandLevel(info.level),
                    },
                });
            }
        }

        lineageNodes = visibleNodes;
        lineageEdges = visibleEdges;
        placeholderNodes = newPlaceholderNodes;
    }

    function createFlowNode(
        node: LineageNode,
        indexInLevel: number,
        countAtLevel: number,
    ): Node {
        if (!lineageData) {
            return {
                id: node.id,
                type: node.isSource ? "source" : "default",
                position: { x: 0, y: 0 },
                data: {
                    label: node.label,
                    level: node.level,
                    isSource: node.isSource,
                },
            };
        }

        // Calculate positions: sources at top, target at bottom
        const maxLevel = Math.max(...lineageData.nodes.map((n) => n.level), 0);
        const BOTTOM_Y = 500; // Target entity position (bottom)
        const TOP_Y = 80; // Sources position (top)
        const LEVEL_SPACING = 120; // Vertical spacing between levels
        const COLUMN_OFFSET = 180; // Base offset per level (keeps columns apart)
        const H_SPACING = 150; // Horizontal spacing between siblings at the same level
        
        // Y position: sources at top, target at bottom
        let yPosition: number;
        if (node.isSource) {
            // Sources always at the very top
            yPosition = TOP_Y;
        } else if (node.level === 0) {
            // Target entity at the bottom
            yPosition = BOTTOM_Y;
        } else {
            // Intermediate models: position from bottom, going up as level increases
            // Level 1 should be above target, level 2 above level 1, etc.
            yPosition = BOTTOM_Y - (node.level * LEVEL_SPACING);
        }
        
        // X position: center siblings for this level and spread them horizontally
        // Example: for 3 siblings, indexes 0,1,2 become offsets -1,0,1.
        const siblingCenterOffset = (countAtLevel - 1) / 2;
        const siblingOffset = (indexInLevel - siblingCenterOffset) * H_SPACING;
        const xPosition = node.level * COLUMN_OFFSET + siblingOffset;
        
        return {
            id: node.id,
            type: node.isSource ? "source" : "default",
            position: { x: xPosition, y: yPosition },
            data: {
                label: node.label,
                level: node.level,
                isSource: node.isSource,
                sourceName: node.sourceName,
            },
        };
    }

    function expandLevel(level: number) {
        expandedLevels = new Set([...expandedLevels, level]);
        updateGraphDisplay();
    }

    function collapseLevel(level: number) {
        const newExpanded = new Set(expandedLevels);
        newExpanded.delete(level);
        expandedLevels = newExpanded;
        updateGraphDisplay();
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onClose();
        }
    }

    function handleEscapeKey(event: KeyboardEvent) {
        if (event.key === "Escape") {
            onClose();
        }
    }

    // Listen for escape key
    $effect(() => {
        if (open) {
            window.addEventListener("keydown", handleEscapeKey);
            return () => {
                window.removeEventListener("keydown", handleEscapeKey);
            };
        }
    });
</script>

{#if open}
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        onclick={handleBackdropClick}
        role="dialog"
        aria-modal="true"
        aria-labelledby="lineage-modal-title"
    >
        <div
            class="bg-white rounded-xl shadow-2xl w-[94vw] h-[92vh] max-w-[1600px] max-h-[920px] border border-gray-200 flex flex-col"
        >
            <!-- Header -->
            <div class="px-5 py-4 flex items-center justify-between border-b border-gray-200 flex-shrink-0">
                <div class="flex items-center gap-2">
                    <Icon icon="lucide:git-branch" class="w-5 h-5 text-primary-600" />
                    <h2 id="lineage-modal-title" class="text-lg font-semibold text-gray-900">
                        Upstream Lineage
                    </h2>
                    {#if modelId}
                        <span class="text-sm text-gray-500 font-mono">{modelId}</span>
                    {/if}
                </div>
                <button
                    class="p-2 rounded-md hover:bg-gray-100 text-gray-700 hover:text-gray-900 transition-colors"
                    onclick={onClose}
                    aria-label="Close"
                    title="Close (Esc)"
                >
                    <Icon icon="lucide:x" class="w-6 h-6 font-bold" />
                </button>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-hidden relative">
                {#if loading}
                    <div class="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                        <div class="flex flex-col items-center gap-3 text-gray-600">
                            <Icon icon="lucide:loader-2" class="w-8 h-8 animate-spin" />
                            <span>Generating lineage...</span>
                        </div>
                    </div>
                {:else if error}
                    <div class="p-5 flex flex-col items-center gap-4">
                        <div class="flex items-center gap-3 text-danger-700 bg-danger-50 border border-danger-200 rounded-lg px-4 py-3">
                            <Icon icon="lucide:alert-triangle" class="w-5 h-5" />
                            <span>{error}</span>
                        </div>
                        {#if error.includes("catalog") || error.includes("Catalog")}
                            <div class="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
                                <p class="font-medium mb-1">To generate lineage, you need to:</p>
                                <code class="block bg-white px-2 py-1 rounded border border-gray-300 mt-2">
                                    dbt docs generate
                                </code>
                            </div>
                        {/if}
                        <button
                            class="px-4 py-2 text-sm rounded-md bg-primary-600 text-white hover:bg-primary-700"
                            onclick={loadLineage}
                        >
                            Retry
                        </button>
                    </div>
                {:else if lineageData && lineageNodes.length > 0}
                    <SvelteFlow
                        nodes={lineageNodes}
                        edges={lineageEdges}
                        nodeTypes={nodeTypes}
                        fitView
                        panOnDrag={true}
                        selectionOnDrag={false}
                        class="w-full h-full"
                    >
                        <Controls />
                        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
                        <MiniMap />
                    </SvelteFlow>
                {:else if lineageData}
                    <div class="p-5 text-center text-gray-500">
                        No upstream dependencies found for this model.
                    </div>
                {/if}
            </div>

        </div>
    </div>
{/if}

