import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AutoSaveService } from './auto-save';
import type { Node, Edge } from '@xyflow/svelte';

// Mock API function
vi.mock('$lib/api', () => ({
    saveDataModel: vi.fn().mockResolvedValue(undefined),
}));

import { saveDataModel as apiSaveDataModel } from '$lib/api';

describe('AutoSaveService', () => {
    let service: AutoSaveService;
    let onSavingChangeMock: ReturnType<typeof vi.fn<(isSaving: boolean) => void>>;
    let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;

    beforeEach(() => {
        vi.useFakeTimers();

        // Set API base URL for flushSync tests
        process.env.VITE_API_BASE = 'http://localhost:8089';

        // Mock global fetch for flushSync tests
        fetchMock = vi.fn<typeof fetch>().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({}),
        } as Response);
        global.fetch = fetchMock as unknown as typeof fetch;

        onSavingChangeMock = vi.fn<(isSaving: boolean) => void>();
        service = new AutoSaveService(400, onSavingChangeMock);
    });

    afterEach(() => {
        vi.runOnlyPendingTimers();
        vi.useRealTimers();
        vi.clearAllMocks();
    });

    describe('constructor', () => {
        it('should use default debounce when not provided', () => {
            const defaultService = new AutoSaveService();
            expect(defaultService).toBeDefined();
        });

        it('should use provided debounce delay', () => {
            const customService = new AutoSaveService(1000);
            expect(customService).toBeDefined();
        });

        it('should initialize with empty last saved state', () => {
            expect(service.getLastSavedState()).toBe('');
        });

        it('should not be saving initially', () => {
            expect(service.isSavingActive()).toBe(false);
        });
    });

    describe('save', () => {
        const mockNodes: Node[] = [
            { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
        ];
        const mockEdges: Edge[] = [];

        it('should schedule debounced save', async () => {
            service.save(mockNodes, mockEdges);

            // Should mark as saving immediately, but not persist yet
            expect(apiSaveDataModel).not.toHaveBeenCalled();
            expect(onSavingChangeMock).toHaveBeenCalledWith(true);

            // Advance timer past debounce delay
            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync();

            // Should trigger save after debounce
            expect(apiSaveDataModel).toHaveBeenCalled();
            expect(onSavingChangeMock).toHaveBeenCalledWith(false);
        });

        it('should cancel previous pending save', () => {
            service.save(mockNodes, mockEdges);
            service.save(mockNodes, mockEdges);

            vi.advanceTimersByTime(400);

            // Should only call once (second call cancelled first)
            expect(apiSaveDataModel).toHaveBeenCalledTimes(1);
        });

        it('should skip save if state has not changed', () => {
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            vi.clearAllMocks();

            // Save again with same state
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);

            expect(apiSaveDataModel).not.toHaveBeenCalled();
        });

        it('should update saving state callback', async () => {
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync();

            expect(onSavingChangeMock).toHaveBeenCalledWith(true);
            expect(onSavingChangeMock).toHaveBeenCalledWith(false);
        });

        it('should use custom debounce delay', () => {
            const customService = new AutoSaveService(1000);
            customService.save(mockNodes, mockEdges);

            vi.advanceTimersByTime(500);
            expect(apiSaveDataModel).not.toHaveBeenCalled();

            vi.advanceTimersByTime(500);
            expect(apiSaveDataModel).toHaveBeenCalled();
        });

        it('should build correct data model payload', async () => {
            const nodes: Node[] = [
                {
                    id: 'entity1',
                    type: 'entity',
                    position: { x: 100, y: 100 },
                    data: {
                        label: 'Test Entity',
                        description: 'Test description',
                        entity_type: 'fact',
                        width: 280,
                        panelHeight: 200,
                        collapsed: false,
                        tags: ['tag1', 'tag2'],
                    },
                },
            ];
            const edges: Edge[] = [];

            service.save(nodes, edges);
            vi.advanceTimersByTime(400);

            expect(apiSaveDataModel).toHaveBeenCalledWith(
                expect.objectContaining({
                    version: 0.1,
                    entities: expect.arrayContaining([
                        expect.objectContaining({
                            id: 'entity1',
                            label: 'Test Entity',
                            description: 'Test description',
                            entity_type: 'fact',
                        }),
                    ]),
                })
            );
        });
    });

    describe('saveNow', () => {
        const mockNodes: Node[] = [
            { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
        ];
        const mockEdges: Edge[] = [];

        it('should cancel pending debounced save', () => {
            service.save(mockNodes, mockEdges);
            service.saveNow(mockNodes, mockEdges);

            vi.advanceTimersByTime(400);

            // saveNow should cancel debounced save
            expect(apiSaveDataModel).toHaveBeenCalledTimes(1);
        });

        it('should trigger immediate save', () => {
            service.saveNow(mockNodes, mockEdges);

            expect(apiSaveDataModel).toHaveBeenCalled();
        });

        it('should update saving state', () => {
            service.saveNow(mockNodes, mockEdges);

            expect(onSavingChangeMock).toHaveBeenCalledWith(true);
        });
    });

    describe('flushSync', () => {
        const mockNodes: Node[] = [
            { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
        ];
        const mockEdges: Edge[] = [];

        it('should cancel pending save', async () => {
            service.save(mockNodes, mockEdges);
            await Promise.resolve(); // Let the timeout be scheduled
            vi.clearAllMocks();

            await service.flushSync(mockNodes, mockEdges);

            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync();
            expect(apiSaveDataModel).not.toHaveBeenCalled();
        });

        it('should resolve immediately', async () => {
            const promise = service.flushSync(mockNodes, mockEdges);
            await expect(promise).resolves.not.toThrow();
        });

        it('should do nothing if state has not changed', async () => {
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync(); // Wait for save to complete
            vi.clearAllMocks();

            await service.flushSync(mockNodes, mockEdges);

            expect(fetchMock).not.toHaveBeenCalled();
        });

        it('should perform synchronous save on state change', async () => {
            vi.mocked(fetchMock).mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({}),
            } as Response);

            await service.flushSync(mockNodes, mockEdges);

            expect(fetchMock).toHaveBeenCalled();
        });

        it('should throw on fetch error', async () => {
            const differentNodes: Node[] = [
                { id: 'node-fetch-error', type: 'entity', position: { x: 100, y: 100 }, data: { label: 'Error Node' } },
            ];
            const error = new TypeError('Network error');
            
            // Ensure state is fresh
            service.clearLastSavedState();
            vi.mocked(fetchMock).mockRejectedValueOnce(error);

            await expect(service.flushSync(differentNodes, mockEdges)).rejects.toThrow('Network error');
        });

        it('should throw on HTTP error', async () => {
            const differentNodes: Node[] = [
                { id: 'node-http-error', type: 'entity', position: { x: 200, y: 200 }, data: { label: 'HTTP Error Node' } },
            ];
            
            // Ensure state is fresh
            service.clearLastSavedState();
            vi.mocked(fetchMock).mockResolvedValueOnce({
                ok: false,
                status: 500,
            } as Response);

            await expect(service.flushSync(differentNodes, mockEdges)).rejects.toThrow('HTTP error! status: 500');
        });
    });

    describe('hasUnsavedChanges', () => {
        const mockNodes: Node[] = [
            { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
        ];
        const mockEdges: Edge[] = [];

        it('should return false when nothing has been saved yet', () => {
            expect(service.hasUnsavedChanges(mockNodes, mockEdges)).toBe(false);
        });

        it('should return false after saving', () => {
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);

            expect(service.hasUnsavedChanges(mockNodes, mockEdges)).toBe(false);
        });

        it('should return true after state changes', () => {
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            vi.clearAllMocks();

            const changedNodes = [
                { ...mockNodes[0], data: { ...mockNodes[0].data, label: 'Changed' } },
            ];

            expect(service.hasUnsavedChanges(changedNodes, mockEdges)).toBe(true);
        });

        it('should return true after adding a node', () => {
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);

            const newNodes = [
                ...mockNodes,
                {
                    id: 'node2',
                    type: 'entity',
                    position: { x: 100, y: 100 },
                    data: { label: 'Node 2' },
                },
            ];

            expect(service.hasUnsavedChanges(newNodes, mockEdges)).toBe(true);
        });

        it('should return true after adding an edge', () => {
            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);

            const newEdges = [
                ...mockEdges,
                { id: 'edge1', source: 'node1', target: 'node2', type: 'custom' },
            ];

            expect(service.hasUnsavedChanges(mockNodes, newEdges)).toBe(true);
        });
    });

    describe('setDebounceMs', () => {
        it('should update debounce delay', () => {
            const mockNodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
            ];
            const mockEdges: Edge[] = [];

            service.setDebounceMs(1000);
            service.save(mockNodes, mockEdges);

            vi.advanceTimersByTime(500);
            expect(apiSaveDataModel).not.toHaveBeenCalled();

            vi.advanceTimersByTime(500);
            expect(apiSaveDataModel).toHaveBeenCalled();
        });
    });

    describe('isSavingActive', () => {
        it('should return false when not saving', () => {
            expect(service.isSavingActive()).toBe(false);
        });

        it('should return true during save', async () => {
            const mockNodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
            ];
            const mockEdges: Edge[] = [];

            service.save(mockNodes, mockEdges);
            // State changes to saving immediately
            expect(service.isSavingActive()).toBe(true);

            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync(); // Flush promises
            // State resets after save completes
            expect(service.isSavingActive()).toBe(false);
        });
    });

    describe('getLastSavedState', () => {
        it('should return empty string initially', () => {
            expect(service.getLastSavedState()).toBe('');
        });

        it('should return state after save', async () => {
            const mockNodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
            ];
            const mockEdges: Edge[] = [];

            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync(); // Flush promises

            const savedState = service.getLastSavedState();
            expect(savedState).toContain('node1');
        });
    });

    describe('clearLastSavedState', () => {
        it('should clear saved state', async () => {
            const mockNodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
            ];
            const mockEdges: Edge[] = [];

            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync(); // Flush promises

            expect(service.getLastSavedState()).toContain('node1');

            service.clearLastSavedState();

            expect(service.getLastSavedState()).toBe('');
        });

        it('should make hasUnsavedChanges return false after clearing', () => {
            const mockNodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
            ];
            const mockEdges: Edge[] = [];

            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);

            service.clearLastSavedState();

            expect(service.hasUnsavedChanges(mockNodes, mockEdges)).toBe(false);
        });
    });

    describe('data model building', () => {
        it('should filter out non-entity nodes', () => {
            const nodes: Node[] = [
                { id: 'entity1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Entity 1' } },
                { id: 'group1', type: 'group', position: { x: 100, y: 100 }, data: { label: 'Group 1' } },
            ];
            const edges: Edge[] = [];

            service.save(nodes, edges);
            vi.advanceTimersByTime(400);

            const dataModelArg = vi.mocked(apiSaveDataModel).mock.calls[0][0];
            expect(dataModelArg.entities.length).toBe(1);
            expect(dataModelArg.entities[0].id).toBe('entity1');
        });

        it('should handle bound model entities', () => {
            const nodes: Node[] = [
                {
                    id: 'entity1',
                    type: 'entity',
                    position: { x: 0, y: 0 },
                    data: {
                        label: 'Entity 1',
                        dbt_model: 'model1',
                        tags: ['tag1'],
                        _schemaTags: ['schema-tag'],
                    },
                },
            ];
            const edges: Edge[] = [];

            service.save(nodes, edges);
            vi.advanceTimersByTime(400);

            const dataModelArg = vi.mocked(apiSaveDataModel).mock.calls[0][0];
            const entity = dataModelArg.entities[0];

            // Bound entities should persist only schema tags
            expect(entity.tags).toEqual(['schema-tag']);
        });

        it('should handle unbound model entities', () => {
            const nodes: Node[] = [
                {
                    id: 'entity1',
                    type: 'entity',
                    position: { x: 0, y: 0 },
                    data: {
                        label: 'Entity 1',
                        tags: ['tag1', 'tag2'],
                    },
                },
            ];
            const edges: Edge[] = [];

            service.save(nodes, edges);
            vi.advanceTimersByTime(400);

            const dataModelArg = vi.mocked(apiSaveDataModel).mock.calls[0][0];
            const entity = dataModelArg.entities[0];

            // Unbound entities should persist display tags
            expect(entity.tags).toEqual(['tag1', 'tag2']);
        });

        it('should handle edges without models', () => {
            const nodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
                { id: 'node2', type: 'entity', position: { x: 100, y: 100 }, data: { label: 'Node 2' } },
            ];
            const edges: Edge[] = [
                {
                    id: 'edge1',
                    source: 'node1',
                    target: 'node2',
                    type: 'custom',
                    data: { label: 'test', type: 'one_to_many' },
                },
            ];

            service.save(nodes, edges);
            vi.advanceTimersByTime(400);

            const dataModelArg = vi.mocked(apiSaveDataModel).mock.calls[0][0];
            expect(dataModelArg.relationships.length).toBe(1);
            expect(dataModelArg.relationships[0].label).toBe('test');
        });

        it('should handle edges with multiple models', () => {
            const nodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
                { id: 'node2', type: 'entity', position: { x: 100, y: 100 }, data: { label: 'Node 2' } },
            ];
            const edges: Edge[] = [
                {
                    id: 'edge1',
                    source: 'node1',
                    target: 'node2',
                    type: 'custom',
                    data: {
                        models: [
                            {
                                source_field: 'field1',
                                target_field: 'field2',
                                source_model_name: 'model1',
                                source_model_version: 1,
                                target_model_name: 'model2',
                                target_model_version: 1,
                            },
                            {
                                source_field: 'field3',
                                target_field: 'field4',
                                source_model_name: 'model3',
                                source_model_version: 2,
                                target_model_name: 'model4',
                                target_model_version: 2,
                            },
                        ],
                    },
                },
            ];

            service.save(nodes, edges);
            vi.advanceTimersByTime(400);

            const dataModelArg = vi.mocked(apiSaveDataModel).mock.calls[0][0];
            expect(dataModelArg.relationships.length).toBe(2);
            expect(dataModelArg.relationships[0].source_field).toBe('field1');
            expect(dataModelArg.relationships[1].source_field).toBe('field3');
        });
    });

    describe('error handling', () => {
        it('should handle save errors gracefully', async () => {
            const error = new Error('Save failed');
            vi.mocked(apiSaveDataModel).mockRejectedValueOnce(error);

            const mockNodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
            ];
            const mockEdges: Edge[] = [];

            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync(); // Flush promises (including rejection)

            // Should not crash and should update state
            expect(onSavingChangeMock).toHaveBeenCalled();
        });

        it('should set isSaving to false after successful save', async () => {
            const mockNodes: Node[] = [
                { id: 'node1', type: 'entity', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
            ];
            const mockEdges: Edge[] = [];

            vi.mocked(apiSaveDataModel).mockResolvedValueOnce(undefined);

            service.save(mockNodes, mockEdges);
            vi.advanceTimersByTime(400);
            await vi.runAllTimersAsync(); // Flush promises

            // Should set saving to false after successful save
            expect(service.isSavingActive()).toBe(false);
            expect(onSavingChangeMock).toHaveBeenCalledWith(false);
        });
    });
});
