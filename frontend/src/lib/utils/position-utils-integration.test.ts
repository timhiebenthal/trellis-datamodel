import { describe, it, expect } from "vitest";
import { calculateSmartPosition } from "./position-utils";
import type { Node } from "@xyflow/svelte";

describe("position-utils integration tests", () => {
    describe("Smart positioning with existing entities", () => {
        it("should position fact entities in center area when entities already exist", () => {
            // Simulate a scenario where entities are at specific positions
            const existingNodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 300, y: 200 },
                    data: { label: "Entity 1" },
                },
                {
                    id: "entity2",
                    type: "entity",
                    position: { x: 700, y: 600 },
                    data: { label: "Entity 2" },
                },
            ];

            const newPosition = calculateSmartPosition("fact", existingNodes);

            // Center should be at (500, 400)
            // Fact should be placed within 200px of center (offset range)
            const dx = newPosition.x - 500;
            const dy = newPosition.y - 400;

            // Check that fact is within expected range from center
            expect(Math.abs(dx)).toBeLessThanOrEqual(200);
            expect(Math.abs(dy)).toBeLessThanOrEqual(200);
        });

        it("should position dimension entities in outer ring around existing entities", () => {
            // Entities clustered around 500, 400
            const existingNodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 450, y: 350 },
                    data: { label: "Entity 1" },
                },
                {
                    id: "entity2",
                    type: "entity",
                    position: { x: 550, y: 450 },
                    data: { label: "Entity 2" },
                },
            ];

            const newPosition = calculateSmartPosition("dimension", existingNodes);

            // Center should be at (500, 400)
            // Dimension should be placed 500-800px from center
            const dx = newPosition.x - 500;
            const dy = newPosition.y - 400;
            const distance = Math.sqrt(dx * dx + dy * dy);

            expect(distance).toBeGreaterThanOrEqual(500);
            expect(distance).toBeLessThanOrEqual(800);
        });

        it("should handle entities spread across large canvas area", () => {
            // Entities spanning a large area
            const existingNodes: Node[] = [
                {
                    id: "entity1",
                    type: "entity",
                    position: { x: 0, y: 0 },
                    data: { label: "Entity 1" },
                },
                {
                    id: "entity2",
                    type: "entity",
                    position: { x: 1000, y: 0 },
                    data: { label: "Entity 2" },
                },
                {
                    id: "entity3",
                    type: "entity",
                    position: { x: 0, y: 800 },
                    data: { label: "Entity 3" },
                },
                {
                    id: "entity4",
                    type: "entity",
                    position: { x: 1000, y: 800 },
                    data: { label: "Entity 4" },
                },
            ];

            const factPosition = calculateSmartPosition("fact", existingNodes);
            const dimPosition = calculateSmartPosition("dimension", existingNodes);

            // Center should be at (500, 400)
            // Fact should be within 200px of center
            const factDx = factPosition.x - 500;
            const factDy = factPosition.y - 400;
            const factDistance = Math.sqrt(factDx * factDx + factDy * factDy);

            expect(factDistance).toBeLessThanOrEqual(Math.sqrt(2) * 200);

            // Dimension should be 500-800px from center
            const dimDx = dimPosition.x - 500;
            const dimDy = dimPosition.y - 400;
            const dimDistance = Math.sqrt(dimDx * dimDx + dimDy * dimDy);

            expect(dimDistance).toBeGreaterThanOrEqual(500);
            expect(dimDistance).toBeLessThanOrEqual(800);
        });

        it("should position multiple entities without clustering at same point", () => {
            const existingNodes: Node[] = [];

            const positions = Array.from({ length: 10 }, (_, i) =>
                calculateSmartPosition("fact", existingNodes),
            );

            // Check that we don't have all positions at the same point
            const uniquePositions = new Set(
                positions.map((p) => `${p.x.toFixed(0)},${p.y.toFixed(0)}`),
            );

            // With random positioning, we should have at least 3 distinct positions
            expect(uniquePositions.size).toBeGreaterThan(2);
        });

        it("should handle dimensional model with mix of entity types", () => {
            // Existing entities of different types
            const existingNodes: Node[] = [
                {
                    id: "fact1",
                    type: "entity",
                    position: { x: 500, y: 400 },
                    data: { label: "Fact 1", entity_type: "fact" },
                },
                {
                    id: "dim1",
                    type: "entity",
                    position: { x: 1000, y: 400 },
                    data: { label: "Dim 1", entity_type: "dimension" },
                },
                {
                    id: "dim2",
                    type: "entity",
                    position: { x: 500, y: 900 },
                    data: { label: "Dim 2", entity_type: "dimension" },
                },
            ];

            const newFactPosition = calculateSmartPosition("fact", existingNodes);
            const newDimPosition = calculateSmartPosition("dimension", existingNodes);

            // Center should be calculated from all entities
            const minX = Math.min(500, 1000, 500);
            const maxX = Math.max(500, 1000, 500);
            const minY = Math.min(400, 400, 900);
            const maxY = Math.max(400, 400, 900);

            const centerX = (minX + maxX) / 2; // 750
            const centerY = (minY + maxY) / 2; // 650

            // New fact should be within 200px of calculated center
            const factDx = newFactPosition.x - centerX;
            const factDy = newFactPosition.y - centerY;
            const factDistance = Math.sqrt(factDx * factDx + factDy * factDy);

            expect(factDistance).toBeLessThanOrEqual(300); // More lenient for this test

            // New dimension should be 500-800px from center
            const dimDx = newDimPosition.x - centerX;
            const dimDy = newDimPosition.y - centerY;
            const dimDistance = Math.sqrt(dimDx * dimDx + dimDy * dimDy);

            expect(dimDistance).toBeGreaterThanOrEqual(500);
            expect(dimDistance).toBeLessThanOrEqual(800);
        });
    });
});
