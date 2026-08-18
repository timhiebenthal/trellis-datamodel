import { expect, test } from '@playwright/test';
import * as fs from 'node:fs';

import { buildBootFixture, BOOT_FIXTURE_COUNTS } from './boot-fixture';

const ARTIFACT_KEYS = ['manifestPath', 'catalogPath', 'dataModelPath', 'layoutPath'] as const;

test('same seed builds byte-equal artifacts with resolving references', async () => {
    const first = buildBootFixture({ seed: 'stream-a' });
    const second = buildBootFixture({ seed: 'stream-a' });

    for (const key of ARTIFACT_KEYS) {
        expect(fs.readFileSync(first[key])).toEqual(fs.readFileSync(second[key]));
    }

    expect(first.counts).toEqual(BOOT_FIXTURE_COUNTS);

    const manifest = JSON.parse(fs.readFileSync(first.manifestPath, 'utf8')) as {
        nodes: Record<string, { columns: Record<string, unknown>; depends_on?: { nodes?: string[] } }>;
        parent_map: Record<string, string[]>;
        child_map: Record<string, string[]>;
    };
    const catalog = JSON.parse(fs.readFileSync(first.catalogPath, 'utf8')) as {
        nodes: Record<string, { columns: Record<string, unknown> }>;
    };
    const dataModel = JSON.parse(fs.readFileSync(first.dataModelPath, 'utf8')) as {
        entities: Array<{ id: string; model_ref: string }>;
        relationships: Array<{ source: string; target: string }>;
    };
    const layout = JSON.parse(fs.readFileSync(first.layoutPath, 'utf8')) as {
        entities: Record<string, unknown>;
        relationships: Record<string, unknown>;
    };

    const modelIds = new Set(Object.keys(manifest.nodes));
    const entityIds = new Set(dataModel.entities.map((entity) => entity.id));

    expect(modelIds.size).toBe(BOOT_FIXTURE_COUNTS.models);
    expect(dataModel.entities).toHaveLength(BOOT_FIXTURE_COUNTS.entities);
    expect(dataModel.relationships).toHaveLength(BOOT_FIXTURE_COUNTS.relationships);
    expect(Object.keys(layout.entities)).toEqual(dataModel.entities.map((entity) => entity.id));
    expect(Object.keys(layout.relationships)).toHaveLength(BOOT_FIXTURE_COUNTS.relationships);

    for (const [modelId, node] of Object.entries(manifest.nodes)) {
        expect(Object.keys(node.columns)).toHaveLength(BOOT_FIXTURE_COUNTS.columnsPerModel);
        expect(catalog.nodes[modelId]).toBeDefined();
        expect(Object.keys(catalog.nodes[modelId].columns)).toHaveLength(
            BOOT_FIXTURE_COUNTS.columnsPerModel,
        );
        for (const dependency of node.depends_on?.nodes ?? []) {
            expect(modelIds.has(dependency)).toBe(true);
        }
        for (const dependency of manifest.parent_map[modelId] ?? []) {
            expect(modelIds.has(dependency)).toBe(true);
        }
        for (const child of manifest.child_map[modelId] ?? []) {
            expect(modelIds.has(child)).toBe(true);
        }
    }

    for (const entity of dataModel.entities) {
        expect(modelIds.has(entity.model_ref)).toBe(true);
        expect(layout.entities[entity.id]).toBeDefined();
    }
    for (const relationship of dataModel.relationships) {
        expect(entityIds.has(relationship.source)).toBe(true);
        expect(entityIds.has(relationship.target)).toBe(true);
    }
});
