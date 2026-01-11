import { describe, it, expect, vi } from "vitest";
import {
    calculateCanvasCenter,
    calculateFactPosition,
    calculateDimensionPosition,
    calculateUnclassifiedPosition,
    calculateSmartPosition,
    isPositionNearEntity,
    findNonOverlappingPosition,
    type Position,
} from "./position-utils";
import type { Node } from "@xyflow/svelte";

describe("position-utils", () => {
    describe("calculateCanvasCenter", () => {
        it("should return default center when no entities exist", () => {
            const nodes: Node[] = [];
            const center = calculateCanvasCenter(nodes);

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
            const center = calculateCanvasCenter(nodes);

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
            const center = calculateCanvasCenter(nodes);

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
            const center = calculateCanvasCenter(nodes);

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
            const center = calculateCanvasCenter(nodes);

            expect(center.x).toBe(500); // (400 + 600) / 2
            expect(center.y).toBe(400); // (300 + 500) / 2
        });

        it("should use custom default center when provided in config", () => {
            const nodes: Node[] = [];
            const center = calculateCanvasCenter(nodes, {
                defaultCenterX: 1000,
                defaultCenterY: 800,
            });

            expect(center.x).toBe(1000);
            expect(center.y).toBe(800);
        });
    });

    describe("calculateFactPosition", () => {
        it("should return position near center", () => {
            const center: Position = { x: 500, y: 400 };
            const position = calculateFactPosition(center);

            expect(position.x).toBeGreaterThan(300); // 500 - 200
            expect(position.x).toBeLessThan(700); // 500 + 200
            expect(position.y).toBeGreaterThan(200); // 400 - 200
            expect(position.y).toBeLessThan(600); // 400 + 200
        });

        it("should use custom offset range from config", () => {
            const center: Position = { x: 500, y: 400 };
            const position = calculateFactPosition(center, { factOffsetRange: 100 });

            expect(position.x).toBeGreaterThan(400); // 500 - 100
            expect(position.x).toBeLessThan(600); // 500 + 100
            expect(position.y).toBeGreaterThan(300); // 400 - 100
            expect(position.y).toBeLessThan(500); // 400 + 100
        });

        it("should generate different positions on multiple calls", () => {
            const center: Position = { x: 500, y: 400 };
            const positions = Array.from({ length: 10 }, () =>
                calculateFactPosition(center),
            );

            const uniquePositions = new Set(
                positions.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`),
            );

            expect(uniquePositions.size).toBeGreaterThan(1);
        });
    });

    describe("calculateDimensionPosition", () => {
        it("should place dimension entity on outer ring", () => {
            const center: Position = { x: 500, y: 400 };
            const position = calculateDimensionPosition(center);

            const dx = position.x - center.x;
            const dy = position.y - center.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            // Distance should be between 500 and 800 (500 + 300)
            expect(distance).toBeGreaterThanOrEqual(500);
            expect(distance).toBeLessThanOrEqual(800);
        });

        it("should use custom radius from config", () => {
            const center: Position = { x: 500, y: 400 };
            const position = calculateDimensionPosition(center, {
                dimensionMinRadius: 200,
                dimensionRadiusOffset: 100,
            });

            const dx = position.x - center.x;
            const dy = position.y - center.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            expect(distance).toBeGreaterThanOrEqual(200);
            expect(distance).toBeLessThanOrEqual(300);
        });

        it("should generate positions at different angles", () => {
            const center: Position = { x: 500, y: 400 };
            const positions = Array.from({ length: 20 }, () =>
                calculateDimensionPosition(center),
            );

            const angles = positions.map((p) => {
                const dx = p.x - center.x;
                const dy = p.y - center.y;
                return Math.atan2(dy, dx);
            });

            // Check that we have good angular coverage
            const minAngle = Math.min(...angles);
            const maxAngle = Math.max(...angles);
            const angleRange = maxAngle - minAngle;

            expect(angleRange).toBeGreaterThan(Math.PI); // Should cover more than 180 degrees
        });

        it("should generate different positions on multiple calls", () => {
            const center: Position = { x: 500, y: 400 };
            const positions = Array.from({ length: 10 }, () =>
                calculateDimensionPosition(center),
            );

            const uniquePositions = new Set(
                positions.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`),
            );

            expect(uniquePositions.size).toBeGreaterThan(1);
        });
    });

    describe("calculateUnclassifiedPosition", () => {
        it("should return position in top-left area", () => {
            const position = calculateUnclassifiedPosition();

            expect(position.x).toBeGreaterThan(100);
            expect(position.x).toBeLessThan(300);
            expect(position.y).toBeGreaterThan(100);
            expect(position.y).toBeLessThan(300);
        });

        it("should generate different positions on multiple calls", () => {
            const positions = Array.from({ length: 10 }, () =>
                calculateUnclassifiedPosition(),
            );

            const uniquePositions = new Set(
                positions.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`),
            );

            expect(uniquePositions.size).toBeGreaterThan(1);
        });
    });

    describe("calculateSmartPosition", () => {
        it("should use fact positioning for fact entity type", () => {
            const nodes: Node[] = [];
            const position = calculateSmartPosition("fact", nodes);

            // Fact entities should be near center (default 500, 400)
            expect(position.x).toBeGreaterThan(300);
            expect(position.x).toBeLessThan(700);
            expect(position.y).toBeGreaterThan(200);
            expect(position.y).toBeLessThan(600);
        });

        it("should use dimension positioning for dimension entity type", () => {
            const nodes: Node[] = [];
            const position = calculateSmartPosition("dimension", nodes);

            // Dimension entities should be on outer ring from default center
            const dx = position.x - 500;
            const dy = position.y - 400;
            const distance = Math.sqrt(dx * dx + dy * dy);

            expect(distance).toBeGreaterThanOrEqual(500);
            expect(distance).toBeLessThanOrEqual(800);
        });

        it("should use unclassified positioning for unclassified entity type", () => {
            const nodes: Node[] = [];
            const position = calculateSmartPosition("unclassified", nodes);

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
            const position = calculateSmartPosition("fact", nodes);

            // Fact should be near the existing entity's center
            expect(position.x).toBeGreaterThan(800);
            expect(position.x).toBeLessThan(1200);
            expect(position.y).toBeGreaterThan(600);
            expect(position.y).toBeLessThan(1000);
        });

        it("should use custom config when provided", () => {
            const nodes: Node[] = [];
            const position = calculateSmartPosition(
                "fact",
                nodes,
                {
                    defaultCenterX: 1000,
                    defaultCenterY: 800,
                    factOffsetRange: 50,
                },
            );

            expect(position.x).toBeGreaterThan(950);
            expect(position.x).toBeLessThan(1050);
            expect(position.y).toBeGreaterThan(750);
            expect(position.y).toBeLessThan(850);
        });
    });

    describe("isPositionNearEntity", () => {
        it("should return false when no entities exist", () => {
            const nodes: Node[] = [];
            const position: Position = { x: 500, y: 400 };

            expect(isPositionNearEntity(position, nodes)).toBe(false);
        });

        it("should return false when position is far from all entities", () => {
            const nodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 100, y: 100 },
                    data: { label: "Entity 1" },
                },
            ];
            const position: Position = { x: 500, y: 400 };

            expect(isPositionNearEntity(position, nodes, 50)).toBe(false);
        });

        it("should return true when position is close to an entity", () => {
            const nodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 500, y: 400 },
                    data: { label: "Entity 1" },
                },
            ];
            const position: Position = { x: 540, y: 430 };

            expect(isPositionNearEntity(position, nodes, 50)).toBe(true);
        });

        it("should ignore group nodes in proximity check", () => {
            const nodes: Node[] = [
                {
                    id: "group1",
                    type: "group",
                    position: { x: 500, y: 400 },
                    data: { label: "Group" },
                },
            ];
            const position: Position = { x: 500, y: 400 };

            expect(isPositionNearEntity(position, nodes, 50)).toBe(false);
        });

        it("should use custom min distance when provided", () => {
            const nodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 500, y: 400 },
                    data: { label: "Entity 1" },
                },
            ];
            const position: Position = { x: 540, y: 430 };

            // Distance is sqrt(40^2 + 30^2) = 50
            expect(isPositionNearEntity(position, nodes, 60)).toBe(true);
            expect(isPositionNearEntity(position, nodes, 40)).toBe(false);
        });

        it("should check all entities", () => {
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
                    position: { x: 200, y: 200 },
                    data: { label: "Entity 2" },
                },
                {
                    id: "entity3",
                    type: "entity",
                    position: { x: 300, y: 300 },
                    data: { label: "Entity 3" },
                },
            ];
            const position: Position = { x: 230, y: 220 };

            expect(isPositionNearEntity(position, nodes, 50)).toBe(true);
        });
    });

    describe("findNonOverlappingPosition", () => {
        it("should return a position when canvas is empty", () => {
            const nodes: Node[] = [];
            const position = findNonOverlappingPosition("fact", nodes);

            expect(position.x).toBeDefined();
            expect(position.y).toBeDefined();
        });

        it("should find a non-overlapping position on first attempt", () => {
            const nodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 100, y: 100 },
                    data: { label: "Entity 1" },
                },
            ];
            const position = findNonOverlappingPosition("fact", nodes);

            // Position should not be near existing entity
            expect(isPositionNearEntity(position, nodes, 50)).toBe(false);
        });

        it("should retry multiple times if needed", () => {
            // Create a scenario where overlap is likely
            const nodes: Node[] = [];
            for (let i = 0; i < 100; i++) {
                nodes.push({
                    id: `entity${i}`,
                    type: "entity",
                    position: { x: 100 + i * 10, y: 100 + i * 10 },
                    data: { label: `Entity ${i}` },
                });
            }

            const position = findNonOverlappingPosition("fact", nodes, 20);

            expect(position.x).toBeDefined();
            expect(position.y).toBeDefined();
        });

        it("should return calculated position after max attempts", () => {
            // Force all attempts to overlap by placing entities in all likely positions
            const nodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 500, y: 400 },
                    data: { label: "Entity 1" },
                },
            ];

            // Even if max attempts is reached, it should return a position
            const position = findNonOverlappingPosition("fact", nodes, 3);

            expect(position.x).toBeDefined();
            expect(position.y).toBeDefined();
        });

        it("should use custom config", () => {
            const nodes: Node[] = [];
            const position = findNonOverlappingPosition("fact", nodes, 10, {
                defaultCenterX: 1000,
                defaultCenterY: 800,
            });

            expect(position.x).toBeGreaterThan(800);
            expect(position.x).toBeLessThan(1200);
            expect(position.y).toBeGreaterThan(600);
            expect(position.y).toBeLessThan(1000);
        });
    });
});
