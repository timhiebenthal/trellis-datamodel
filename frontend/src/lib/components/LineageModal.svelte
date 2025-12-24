<script lang="ts">
    import { onMount } from "svelte";
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

        // Get max level
        const maxLevel = Math.max(...lineageData.nodes.map((n) => n.level), 0);

        // Process nodes - show all nodes initially (no progressive filtering for now)
        // Sources should always be visible
        for (const node of lineageData.nodes) {
            // Always show sources, root, and direct dependencies
            if (node.isSource || node.level === 0 || node.level === 1) {
                visibleNodes.push(createFlowNode(node));
            } else if (expandedLevels.size === 0 || expandedLevels.has(node.level)) {
                // Show if no filtering or if level is expanded
                visibleNodes.push(createFlowNode(node));
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
                        y: parentNode.position.y + 100,
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

    function createFlowNode(node: LineageNode): Node {
        return {
            id: node.id,
            type: node.isSource ? "source" : "default",
            position: { x: node.level * 200, y: Math.random() * 300 }, // Basic layout - will be improved
            data: {
                label: node.label,
                level: node.level,
                isSource: node.isSource,
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
        <div class="bg-white rounded-xl shadow-2xl w-[99.5vw] h-[98vh] border border-gray-200 flex flex-col">
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

