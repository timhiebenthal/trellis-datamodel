import { describe, it, expect, vi, beforeEach } from 'vitest';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Node, Edge } from '@xyflow/svelte';
import { AutoSaveService } from './auto-save';

/**
 * Save contract: the REAL buildDataModel output, serialized through the REAL
 * api.saveDataModel (JSON.stringify drops `undefined` keys), is compared to
 * golden payloads that the backend test
 * (trellis_datamodel/tests/test_frontend_save_contract.py) POSTs verbatim.
 *
 * Regenerate after an intentional payload change:
 *   UPDATE_SAVE_CONTRACT=1 npm run test:unit -- save-contract
 */

// vitest cwd is frontend/; goldens live in the backend test fixtures.
const GOLDEN_DIR = resolve(
    process.cwd(),
    '..',
    'trellis_datamodel',
    'tests',
    'fixtures',
    'frontend_save_payloads',
);
const UPDATE = process.env.UPDATE_SAVE_CONTRACT === '1';

const entityNode = (id: string, data: Record<string, unknown>, x = 10, y = 20): Node => ({
    id,
    type: 'entity',
    position: { x, y },
    data: { label: id, width: 300, panelHeight: 200, collapsed: false, ...data },
});

const scenarios: Record<string, { nodes: Node[]; edges: Edge[] }> = {
    unbound_entity: {
        nodes: [
            entityNode('customer', {
                label: 'Customer',
                description: 'A buyer',
                tags: ['core', 'pii'],
                entity_type: 'dimension',
                source_system: ['SAP'],
                roles: [{ label: 'Buyer', role: 'buyer', source: 'user' }],
                drafted_fields: [
                    {
                        name: 'customer_id',
                        datatype: 'int',
                        description: 'Key',
                        origin: [{ system: 'SAP' }, { table: 'KNA1' }],
                    },
                ],
            }),
        ],
        edges: [],
    },
    bound_entity: {
        nodes: [
            entityNode('orders', {
                label: 'Orders',
                model_ref: 'model.proj.orders',
                // reconcile-owned and display `tags` must never be sent for bound entities
                framework_tags: ['nightly'],
                tags: ['nightly', 'finance'],
                ui_tags: ['finance'],
                entity_type: 'fact',
                source_system: ['SAP'],
                roles: [{ label: 'Order', role: 'order', source: 'dbt' }],
            }),
        ],
        edges: [],
    },
    bound_entity_ui_tags_cleared: {
        nodes: [
            entityNode('orders', {
                label: 'Orders',
                model_ref: 'model.proj.orders',
                framework_tags: ['nightly'],
                tags: ['nightly'],
                ui_tags: [],
                entity_type: 'fact',
                roles: [{ label: 'Order', role: 'order', source: 'dbt' }],
            }),
        ],
        edges: [],
    },
    bound_entity_roles_omitted: {
        nodes: [
            entityNode('orders', {
                label: 'Orders',
                model_ref: 'model.proj.orders',
                ui_tags: ['finance'],
                entity_type: 'fact',
            }),
        ],
        edges: [],
    },
};

async function realFetchBody(nodes: Node[], edges: Edge[]): Promise<unknown> {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue({
        ok: true,
        text: () => Promise.resolve(''),
    } as Response);
    global.fetch = fetchMock as unknown as typeof fetch;

    const service = new AutoSaveService(0);
    // Real buildDataModel + real api.saveDataModel (serialization path of the app).
    await (service as any).persistDataModel(nodes, edges, 'state');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/data-model$/);
    expect(init?.method).toBe('POST');
    return JSON.parse(init?.body as string);
}

describe('frontend save payload contract (goldens shared with backend)', () => {
    beforeEach(() => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    for (const [name, { nodes, edges }] of Object.entries(scenarios)) {
        it(`${name} matches golden payload`, async () => {
            const actual = await realFetchBody(nodes, edges);
            const goldenPath = resolve(GOLDEN_DIR, `${name}.json`);

            if (UPDATE) {
                mkdirSync(GOLDEN_DIR, { recursive: true });
                writeFileSync(goldenPath, JSON.stringify(actual, null, 2) + '\n');
            }
            if (!existsSync(goldenPath)) {
                throw new Error(
                    `Missing golden ${goldenPath}. Run with UPDATE_SAVE_CONTRACT=1 to create it.`,
                );
            }
            const golden = JSON.parse(readFileSync(goldenPath, 'utf-8'));
            try {
                expect(actual).toEqual(golden);
            } catch (e) {
                throw new Error(
                    `Save payload for "${name}" no longer matches ${goldenPath}. ` +
                        'The backend contract test replays this file. Review the diff; if the ' +
                        'change is intended, regenerate with UPDATE_SAVE_CONTRACT=1 and check ' +
                        'trellis_datamodel/tests/test_frontend_save_contract.py still holds.\n' +
                        (e as Error).message,
                );
            }
        });
    }
});
