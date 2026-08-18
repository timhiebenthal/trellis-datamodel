import type { Edge, Node } from "@xyflow/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

const elkState = vi.hoisted(() => ({
    moduleLoads: 0,
    constructorCalls: 0,
    layoutCalls: 0,
}));

const entity = (id: string, x = 0, y = 0): Node =>
    ({
        id,
        type: "entity",
        position: { x, y },
        data: {},
    }) as Node;

const noEdges: Edge[] = [];

describe("applyDagreLayout", () => {
    beforeEach(() => {
        vi.resetModules();
        elkState.moduleLoads = 0;
        elkState.constructorCalls = 0;
        elkState.layoutCalls = 0;
        vi.doMock("elkjs/lib/elk.bundled.js", () => {
            elkState.moduleLoads += 1;

            class MockElk {
                constructor() {
                    elkState.constructorCalls += 1;
                }

                async layout<T>(graph: T): Promise<T> {
                    elkState.layoutCalls += 1;
                    return graph;
                }
            }

            return { default: MockElk };
        });
    });

    it("does not load elkjs when importing the layout module", async () => {
        await import("./layout");

        expect(elkState.moduleLoads).toBe(0);
    });

    it("dynamically loads ELK once for the first layout request", async () => {
        const { applyDagreLayout } = await import("./layout");

        await applyDagreLayout([entity("new")], noEdges);

        expect(elkState.moduleLoads).toBe(1);
        expect(elkState.constructorCalls).toBe(1);
        expect(elkState.layoutCalls).toBe(1);
    });

    it("reuses the loaded ELK constructor for later requests", async () => {
        const { applyDagreLayout } = await import("./layout");

        await applyDagreLayout([entity("first")], noEdges);
        await applyDagreLayout([entity("second")], noEdges);

        expect(elkState.moduleLoads).toBe(1);
        expect(elkState.constructorCalls).toBe(1);
        expect(elkState.layoutCalls).toBe(2);
    });

    it("skips ELK for empty or already-positioned graphs", async () => {
        const { applyDagreLayout } = await import("./layout");
        const positionedNodes = [entity("positioned", 100, 200)];

        expect(await applyDagreLayout([], noEdges)).toEqual([]);
        expect(await applyDagreLayout(positionedNodes, noEdges)).toBe(
            positionedNodes,
        );
        expect(elkState.moduleLoads).toBe(0);
        expect(elkState.constructorCalls).toBe(0);
        expect(elkState.layoutCalls).toBe(0);
    });
});
