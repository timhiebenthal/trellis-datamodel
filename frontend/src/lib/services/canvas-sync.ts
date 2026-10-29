import type { Edge, Node } from "@xyflow/svelte";
import type { ModelInfo, Relationship } from "$lib/types";
import { inferRelationships, syncDbtTests } from "$lib/api";
import { getModelFolder } from "$lib/utils/folder-utils";
import { mergeRelationshipIntoEdges } from "$lib/utils/relationship-edges";
import { formatModelNameForLabel } from "$lib/utils/model-naming";
import { normalizeTags } from "$lib/utils/entity-tags";
import {
    getIncompleteEntities,
    getEntitiesWithUndescribedAttributes,
    shouldShowValidationModal,
} from "$lib/services/entity-validation";

/** Status line for the toolbar plus how long it stays visible. */
export interface SyncStatus {
    message: string;
    clearAfterMs: number;
}

export type UndescribedEntity = { entityLabel: string; entityId: string; attributeNames: string[] };

export interface PushDeps {
    nodes: Node[];
    pushWarningEnabled: boolean;
    confirmIncomplete: (entities: Node[]) => Promise<boolean>;
    confirmUndescribed: (entities: UndescribedEntity[]) => Promise<boolean>;
}

/**
 * Push the data model to the framework (sync relationship tests), first
 * asking the user to confirm when guidance flags incomplete entities or
 * undescribed attributes. Resolves `null` when the user cancels.
 */
export async function pushToFramework(
    deps: PushDeps,
): Promise<(SyncStatus & { ok: boolean }) | null> {
    try {
        const incompleteEntities = getIncompleteEntities(deps.nodes);
        const entitiesWithUndescribed = getEntitiesWithUndescribedAttributes(deps.nodes);

        if (deps.pushWarningEnabled && shouldShowValidationModal(deps.nodes, true, true)) {
            if (incompleteEntities.length > 0) {
                const proceed = await deps.confirmIncomplete(incompleteEntities);
                if (!proceed) return null;
            }
            if (entitiesWithUndescribed.length > 0) {
                const proceed = await deps.confirmUndescribed(entitiesWithUndescribed);
                if (!proceed) return null;
            }
        }

        const result = await syncDbtTests();
        for (const warning of result.warnings ?? []) {
            console.warn("[trellis] sync warning:", warning);
        }
        return { ok: true, message: `✓ ${result.message}`, clearAfterMs: 3000 };
    } catch (e) {
        return {
            ok: false,
            message: `✗ ${e instanceof Error ? e.message : "Sync failed"}`,
            clearAfterMs: 5000,
        };
    }
}

export interface CanvasGraph {
    nodes: Node[];
    edges: Edge[];
    models: ModelInfo[];
    labelPrefixes: string[];
}

export interface MergeResult {
    nodes: Node[];
    edges: Edge[];
    addedRelationships: number;
    addedNodes: number;
}

/**
 * Merge inferred relationships into the canvas: aggregate them into edges and
 * add an entity node for every endpoint not yet on the canvas.
 */
export function mergeInferredRelationships(
    inferred: Relationship[],
    graph: CanvasGraph,
): MergeResult {
    let nodes = graph.nodes;
    let edges = [...graph.edges];
    let addedRelationships = 0;
    let addedNodes = 0;
    const existingEntityIds = new Set(
        nodes.filter((n) => n.type === "entity").map((n) => n.id),
    );

    function maybeAddEntity(id: string | undefined | null) {
        if (!id) return;
        if (existingEntityIds.has(id)) return;

        const model =
            graph.models.find(
                (m) => m.unique_id === id || m.name === id,
            ) ?? null;
        const folder = model ? getModelFolder(model) : null;

        const newNode: Node = {
            id,
            type: "entity",
            position: { x: 200 + addedNodes * 60, y: 200 },
            zIndex: 10,
            data: {
                label: formatModelNameForLabel((model?.name ?? id).trim(), graph.labelPrefixes),
                description: model?.description ?? "",
                model_ref: model?.unique_id ?? null,
                additional_models: [],
                drafted_fields: [],
                width: 280,
                panelHeight: 200,
                collapsed: false,
                folder,
                tags: normalizeTags(model?.tags),
            },
        };

        nodes = [...nodes, newNode];
        existingEntityIds.add(id);
        addedNodes += 1;
    }

    inferred.forEach((r) => {
        maybeAddEntity(r.source);
        maybeAddEntity(r.target);

        // Merge relationship into edges (will aggregate by entity pair)
        const beforeCount = edges.length;
        edges = mergeRelationshipIntoEdges(edges, r);
        if (edges.length > beforeCount) {
            addedRelationships++;
        }
    });

    return { nodes, edges, addedRelationships, addedNodes };
}

export interface PullDeps {
    /** Read the current canvas once relationships have been inferred. */
    getGraph: () => CanvasGraph;
    noRelationshipsMessage: string;
}

/**
 * Pull relationships from the framework and merge them into the canvas.
 * `nodes` / `edges` are set only when the canvas should be updated.
 */
export async function pullFromFramework(
    deps: PullDeps,
): Promise<SyncStatus & { nodes?: Node[]; edges?: Edge[] }> {
    try {
        const inferred = await inferRelationships();
        if (inferred.length === 0) {
            return { message: deps.noRelationshipsMessage, clearAfterMs: 3000 };
        }

        const merged = mergeInferredRelationships(inferred, deps.getGraph());
        const { addedRelationships, addedNodes } = merged;
        if (addedRelationships === 0 && addedNodes === 0) {
            return { message: "✓ No new relationships found", clearAfterMs: 3000 };
        }
        return {
            nodes: addedNodes > 0 ? merged.nodes : undefined,
            edges: merged.edges,
            message: `✓ Added ${addedRelationships} relationship${addedRelationships !== 1 ? 's' : ''}${addedNodes ? `, ${addedNodes} node${addedNodes !== 1 ? 's' : ''}` : ""}`,
            clearAfterMs: 3000,
        };
    } catch (e) {
        console.error(e);
        return { message: "✗ Failed to infer", clearAfterMs: 5000 };
    }
}
