import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    DimensionalModelPositioner,
    GroupSizeCalculator,
    type DimensionalModelConfig,
    type GroupSizeResult,
    type GroupSizesResult,
} from "./position-calculator";
import type { Node } from "@xyflow/svelte";

describe("position-calculator", () => {
    describe("DimensionalModelPositioner", () => {
        let positioner: DimensionalModelPositioner;

        beforeEach(() => {
            positioner = new DimensionalModelPositioner();
        });

        describe("calculateCenter", () => {
            it("should return default center when no entities exist", () => {
                const nodes: Node[] = [];
                const center = positioner.calculateCenter(nodes);

                expect(center.x).toBe(500);
                expect(center.y).toBe(400);
            });

            it("should return default center when only group nodes exist", () => {
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 100, y: 100 },
                        data: { label: "Group" },
                    },
                ];
                const center = positioner.calculateCenter(nodes);

                expect(center.x).toBe(500);
                expect(center.y).toBe(400);
            });

            it("should calculate center point for single entity", () => {
                const nodes: Node[] = [
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 600, y: 500 },
                        data: { label: "Entity 1" },
                    },
                ];
                const center = positioner.calculateCenter(nodes);

                expect(center.x).toBe(600);
                expect(center.y).toBe(500);
            });

            it("should calculate midpoint between multiple entities", () => {
                const nodes: Node[] = [
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 100, y: 100 },
                        data: { label: "Entity 1" },
                    },
                    {
                        id: "entity2",
                        type: "entity",
                        position: { x: 300, y: 100 },
                        data: { label: "Entity 2" },
                    },
                    {
                        id: "entity3",
                        type: "entity",
                        position: { x: 200, y: 300 },
                        data: { label: "Entity 3" },
                    },
                ];
                const center = positioner.calculateCenter(nodes);

                expect(center.x).toBe(200); // (100 + 300) / 2
                expect(center.y).toBe(200); // (100 + 300) / 2
            });

            it("should ignore group nodes in center calculation", () => {
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group" },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 400, y: 300 },
                        data: { label: "Entity 1" },
                    },
                    {
                        id: "entity2",
                        type: "entity",
                        position: { x: 600, y: 500 },
                        data: { label: "Entity 2" },
                    },
                ];
                const center = positioner.calculateCenter(nodes);

                expect(center.x).toBe(500); // (400 + 600) / 2
                expect(center.y).toBe(400); // (300 + 500) / 2
            });

            it("should use custom default center when provided in config", () => {
                const config: DimensionalModelConfig = {
                    defaultCenterX: 1000,
                    defaultCenterY: 800,
                };
                positioner = new DimensionalModelPositioner(config);

                const nodes: Node[] = [];
                const center = positioner.calculateCenter(nodes);

                expect(center.x).toBe(1000);
                expect(center.y).toBe(800);
            });
        });

        describe("calculateSmartPosition", () => {
            it("should position fact entities near center", () => {
                const nodes: Node[] = [];
                const position = positioner.calculateSmartPosition("fact", nodes);

                // Fact entities should be near default center (500, 400) with offset range 200
                expect(position.x).toBeGreaterThan(300);
                expect(position.x).toBeLessThan(700);
                expect(position.y).toBeGreaterThan(200);
                expect(position.y).toBeLessThan(600);
            });

            it("should position dimension entities on outer ring", () => {
                const nodes: Node[] = [];
                const position = positioner.calculateSmartPosition("dimension", nodes);

                // Dimension entities should be on outer ring from default center
                const dx = position.x - 500;
                const dy = position.y - 400;
                const distance = Math.sqrt(dx * dx + dy * dy);

                expect(distance).toBeGreaterThanOrEqual(500);
                expect(distance).toBeLessThanOrEqual(800);
            });

            it("should position unclassified entities in top-left", () => {
                const nodes: Node[] = [];
                const position = positioner.calculateSmartPosition("unclassified", nodes);

                expect(position.x).toBeGreaterThan(100);
                expect(position.x).toBeLessThan(300);
                expect(position.y).toBeGreaterThan(100);
                expect(position.y).toBeLessThan(300);
            });

            it("should calculate center based on existing entities", () => {
                const nodes: Node[] = [
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 1000, y: 800 },
                        data: { label: "Entity 1" },
                    },
                ];
                const position = positioner.calculateSmartPosition("fact", nodes);

                // Fact should be near existing entity's center
                expect(position.x).toBeGreaterThan(800);
                expect(position.x).toBeLessThan(1200);
                expect(position.y).toBeGreaterThan(600);
                expect(position.y).toBeLessThan(1000);
            });

            it("should handle multiple entities for center calculation", () => {
                const nodes: Node[] = [
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 100, y: 100 },
                        data: { label: "Entity 1" },
                    },
                    {
                        id: "entity2",
                        type: "entity",
                        position: { x: 300, y: 100 },
                        data: { label: "Entity 2" },
                    },
                ];
                const position = positioner.calculateSmartPosition("fact", nodes);

                // Center should be at (200, 100), fact near there
                expect(position.x).toBeGreaterThan(0);
                expect(position.x).toBeLessThan(400);
                expect(position.y).toBeGreaterThan(-100);
                expect(position.y).toBeLessThan(300);
            });

            it("should ignore group nodes in center calculation", () => {
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1" },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 600, y: 400 },
                        data: { label: "Entity 1" },
                    },
                    {
                        id: "entity2",
                        type: "entity",
                        position: { x: 800, y: 500 },
                        data: { label: "Entity 2" },
                    },
                ];
                const position = positioner.calculateSmartPosition("fact", nodes);

                // Should center on entities only, not group
                // Entities at (600,400) and (800,500), center = (700, 450)
                // Fact offset range is 200, so x in [500, 900], y in [250, 650]
                expect(position.x).toBeGreaterThan(400);
                expect(position.x).toBeLessThan(1000);
                expect(position.y).toBeGreaterThan(200);
                expect(position.y).toBeLessThan(700);
            });

        it("should use custom config values", () => {
            positioner = new DimensionalModelPositioner({
                defaultCenterX: 500,
                defaultCenterY: 400,
            });
            const nodes: Node[] = [];
            const position = positioner.calculateSmartPosition("fact", nodes);

            // Fact position should be within factOffsetRange (200px hardcoded) of center
            // Center is (500, 400), so expect x in [300, 700], y in [200, 600]
            expect(position.x).toBeGreaterThanOrEqual(300);
            expect(position.x).toBeLessThanOrEqual(700);
            expect(position.y).toBeGreaterThanOrEqual(200);
            expect(position.y).toBeLessThanOrEqual(600);
        });

            it("should generate different positions on multiple calls", () => {
                const nodes: Node[] = [];
                const positions = Array.from({ length: 10 }, () =>
                    positioner.calculateSmartPosition("fact", nodes),
                );

                const uniquePositions = new Set(
                    positions.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`),
                );

                expect(uniquePositions.size).toBeGreaterThan(1);
            });

            it("should return correct center when no entities exist", () => {
                const nodes: Node[] = [];
                const center = positioner.calculateCenter(nodes);

                expect(center.x).toBe(500);
                expect(center.y).toBe(400);
            });

            it("should calculate midpoint of entity positions", () => {
                const nodes: Node[] = [
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 400, y: 300 },
                        data: { label: "Entity 1" },
                    },
                    {
                        id: "entity2",
                        type: "entity",
                        position: { x: 600, y: 500 },
                        data: { label: "Entity 2" },
                    },
                ];
                const center = positioner.calculateCenter(nodes);

                // (400 + 600) / 2 = 500, (300 + 500) / 2 = 400
                expect(center.x).toBe(500);
                expect(center.y).toBe(400);
            });
        });
    });

    describe("GroupSizeCalculator", () => {
        let calculator: GroupSizeCalculator;

        beforeEach(() => {
            calculator = new GroupSizeCalculator();
        });

        describe("constructor", () => {
            it("should use default config when none provided", () => {
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200 },
                        parentId: "group1",
                        measured: { width: 280, height: 200 },
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                // With measured dimensions, should calculate size based on child
                expect(result.sizes.size).toBe(1);
                const update = result.sizes.get("group1");
                expect(update?.width).toBe(340); // 280 + 20 + 40 padding
                expect(update?.height).toBe(260); // 200 + 20 + 40 padding
            });

            it("should use provided config", () => {
                const config: DimensionalModelConfig = {
                    groupPadding: 50,
                    minGroupWidth: 400,
                };
                calculator = new GroupSizeCalculator(config);

                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 400, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 10, y: 10 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200 },
                        parentId: "group1",
                        measured: { width: 280, height: 200 },
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                // Should need update to accommodate larger padding (50 instead of 40)
                expect(result.sizes.size).toBe(1);
                const update = result.sizes.get("group1");
                expect(update?.width).toBe(400); // 280 + 10 + 50 padding, but minGroupWidth is 400
                expect(update?.height).toBe(260); // 200 + 10 + 50 padding (measured height used directly)
            });
        });

        describe("calculateGroupSizes", () => {
            it("should return empty map when no groups exist", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 0, y: 0 },
                        data: { label: "Entity 1" },
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(0);
                expect(result.needsUpdate).toBe(false);
            });

            it("should return empty map when dragging", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 50, y: 50 },
                        data: { label: "Entity 1" },
                        parentId: "group1",
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", true);

                expect(result.sizes.size).toBe(0);
                expect(result.needsUpdate).toBe(false);
            });

            it("should return empty map when any node is dragging", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 50, y: 50 },
                        data: { label: "Entity 1" },
                        parentId: "group1",
                        dragging: true,
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(0);
                expect(result.needsUpdate).toBe(false);
            });

            it("should return empty map when groups are collapsed", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: true },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 50, y: 50 },
                        data: { label: "Entity 1" },
                        parentId: "group1",
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(0);
                expect(result.needsUpdate).toBe(false);
            });

            it("should skip manually resized groups", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, manuallyResized: true, width: 500, height: 400 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 50, y: 50 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200 },
                        parentId: "group1",
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(0);
                expect(result.needsUpdate).toBe(false);
            });

            it("should return empty map when groups have no visible children", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false },
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(0);
                expect(result.needsUpdate).toBe(false);
            });

            it("should calculate group size based on children with measured dimensions", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1" },
                        parentId: "group1",
                        measured: { width: 280, height: 200 },
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(1);
                expect(result.needsUpdate).toBe(true);
                const update = result.sizes.get("group1");
                expect(update?.width).toBe(340); // 280 + 20 + 40 padding
                expect(update?.height).toBe(260); // 200 + 20 + 40 padding
            });

            it("should calculate group size based on children with data dimensions", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200 },
                        parentId: "group1",
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(1);
                expect(result.needsUpdate).toBe(true);
                const update = result.sizes.get("group1");
                expect(update?.width).toBe(340); // 280 + 20 + 40 padding (using data width)
                expect(update?.height).toBe(260); // 200 (estimated) + 20 + 40 padding (no measured height)
            });

            it("should add extra height for logical view metadata", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200, collapsed: false, dbt_model: { name: "model1" } },
                        parentId: "group1",
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "logical", false);

                expect(result.sizes.size).toBe(1);
                expect(result.needsUpdate).toBe(true);
                const update = result.sizes.get("group1");
                expect(update?.height).toBe(440); // 200 panelHeight + 80 header + 100 logical extra + 20 (position.y) + 40 padding
            });

            it("should enforce minimum dimensions", () => {
                const calculator = new GroupSizeCalculator({ minGroupWidth: 350, minGroupHeight: 250 });
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 0, y: 0 },
                        data: { label: "Entity 1", width: 100, panelHeight: 50 },
                        parentId: "group1",
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(1);
                const update = result.sizes.get("group1");
                expect(update?.width).toBe(350); // max(100 + 0 + 40, 350) = 350 (minGroupWidth enforced)
                expect(update?.height).toBe(250); // max(10 + 80 + 0 + 40, 250) = 250 (minGroupHeight enforced)
            });

            it("should only update if change is significant", () => {
                const nodeWithMeasured = {
                    id: "entity1",
                    type: "entity",
                    position: { x: 20, y: 20 },
                    data: { label: "Entity 1", width: 280, panelHeight: 200 },
                    parentId: "group1",
                } as Node & { measured?: { width: number; height: number } };

                // Set measured >= 50 so we don't estimate
                nodeWithMeasured.measured = { width: 280, height: 280 };

                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 340, height: 340 }, // Already calculated size
                    },
                    nodeWithMeasured,
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(0); // No significant change (within 5px threshold)
                expect(result.needsUpdate).toBe(false);
            });

            it("should handle multiple children", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 200, panelHeight: 150 },
                        parentId: "group1",
                        measured: { width: 200, height: 150 },
                    },
                    {
                        id: "entity2",
                        type: "entity",
                        position: { x: 250, y: 20 },
                        data: { label: "Entity 2", width: 200, panelHeight: 150 },
                        parentId: "group1",
                        measured: { width: 200, height: 150 },
                    },
                    {
                        id: "entity3",
                        type: "entity",
                        position: { x: 20, y: 200 },
                        data: { label: "Entity 3", width: 200, panelHeight: 150 },
                        parentId: "group1",
                        measured: { width: 200, height: 150 },
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(1);
                const update = result.sizes.get("group1");
                expect(update?.width).toBe(490); // 250 + 200 rightmost + 40 padding
                expect(update?.height).toBe(390); // 200 + 150 bottom + 40 padding
            });

            it("should handle multiple groups", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "group2",
                        type: "group",
                        position: { x: 600, y: 0 },
                        data: { label: "Group 2", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200 },
                        parentId: "group1",
                        measured: { width: 280, height: 200 },
                    },
                    {
                        id: "entity2",
                        type: "entity",
                        position: { x: 620, y: 20 },
                        data: { label: "Entity 2", width: 280, panelHeight: 200 },
                        parentId: "group2",
                        measured: { width: 280, height: 200 },
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(2);
                expect(result.needsUpdate).toBe(true);
                expect(result.sizes.has("group1")).toBe(true);
                expect(result.sizes.has("group2")).toBe(true);
            });

            it("should ignore hidden children", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200 },
                        parentId: "group1",
                        hidden: true,
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(0); // No visible children
                expect(result.needsUpdate).toBe(false);
            });

            it("should estimate height for collapsed nodes in data", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", collapsed: false, width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 280, panelHeight: 200, collapsed: false },
                        parentId: "group1",
                        measured: { width: 280, height: 40 }, // Too small, not collapsed
                    },
                ];

                const result = calculator.calculateGroupSizes(nodes, "conceptual", false);

                expect(result.sizes.size).toBe(1);
                const update = result.sizes.get("group1");
                expect(update?.height).toBe(340); // 200 + 60 header + 20 pos + 40 padding (estimated)
            });
        });

        describe("applyGroupSizes", () => {
            it("should return original nodes when no updates", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 0, y: 0 },
                        data: { label: "Entity 1" },
                    },
                ];

                const updated = calculator.applyGroupSizes(nodes, new Map());

                expect(updated).toEqual(nodes);
            });

            it("should apply size updates to groups", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1" },
                        parentId: "group1",
                    },
                ];

                const sizes = new Map<string, GroupSizeResult>([
                    ["group1", { groupId: "group1", width: 400, height: 300 }],
                ]);

                const updated = calculator.applyGroupSizes(nodes, sizes);

                expect(updated).toHaveLength(2);
                const updatedGroup = updated.find((n) => n.id === "group1");
                expect(updatedGroup?.data.width).toBe(400);
                expect(updatedGroup?.data.height).toBe(300);
            });

            it("should not affect non-group nodes", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", width: 300, height: 200 },
                    },
                    {
                        id: "entity1",
                        type: "entity",
                        position: { x: 20, y: 20 },
                        data: { label: "Entity 1", width: 280, height: 200 },
                        parentId: "group1",
                    },
                ];

                const sizes = new Map<string, GroupSizeResult>([
                    ["group1", { groupId: "group1", width: 400, height: 350 }],
                ]);

                const updated = calculator.applyGroupSizes(nodes, sizes);

                const entity = updated.find((n) => n.id === "entity1");
                expect(entity?.data.width).toBe(280);
                expect(entity?.data.height).toBe(200);
            });

            it("should apply multiple size updates", () => {
                const calculator = new GroupSizeCalculator();
                const nodes: Node[] = [
                    {
                        id: "group1",
                        type: "group",
                        position: { x: 0, y: 0 },
                        data: { label: "Group 1", width: 300, height: 200, collapsed: false },
                    },
                    {
                        id: "group2",
                        type: "group",
                        position: { x: 600, y: 0 },
                        data: { label: "Group 2", width: 300, height: 200, collapsed: false },
                    },
                ];

                const sizes = new Map<string, GroupSizeResult>([
                    ["group1", { groupId: "group1", width: 400, height: 350 }],
                    ["group2", { groupId: "group2", width: 500, height: 300 }],
                ]);

                const updated = calculator.applyGroupSizes(nodes, sizes);

                expect(updated[0].data.width).toBe(400);
                expect(updated[0].data.height).toBe(350);
                expect(updated[0].data.collapsed).toBe(false);
            });
        });
    });
});
