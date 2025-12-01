import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { get } from 'svelte/store';
import { nodes, edges, canUndo, canRedo, pushHistory, initHistory, undo, redo } from './stores';

describe('Undo/Redo History', () => {
    beforeEach(() => {
        // Reset stores to initial state
        nodes.set([]);
        edges.set([]);
        // Initialize history with empty state
        initHistory();
        // Use fake timers to control debounce
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('initializes with canUndo=false and canRedo=false', () => {
        expect(get(canUndo)).toBe(false);
        expect(get(canRedo)).toBe(false);
    });

    it('pushHistory enables undo after state change', async () => {
        // Make a change
        nodes.set([{ id: 'node1', position: { x: 0, y: 0 }, data: {} }]);
        pushHistory();

        // Fast-forward debounce timer
        vi.advanceTimersByTime(400);

        expect(get(canUndo)).toBe(true);
        expect(get(canRedo)).toBe(false);
    });

    it('undo restores previous state', async () => {
        // Initial state (empty)
        const initialNodes = get(nodes);

        // Add a node
        nodes.set([{ id: 'node1', position: { x: 100, y: 100 }, data: {} }]);
        pushHistory();
        vi.advanceTimersByTime(400);

        // Undo
        undo();

        expect(get(nodes)).toEqual(initialNodes);
        expect(get(canUndo)).toBe(false);
        expect(get(canRedo)).toBe(true);
    });

    it('redo restores undone state', async () => {
        // Add a node
        const nodeData = [{ id: 'node1', position: { x: 100, y: 100 }, data: {} }];
        nodes.set(nodeData);
        pushHistory();
        vi.advanceTimersByTime(400);

        // Undo then redo
        undo();
        redo();

        expect(get(nodes)).toEqual(nodeData);
        expect(get(canUndo)).toBe(true);
        expect(get(canRedo)).toBe(false);
    });

    it('undo does nothing when at beginning of history', () => {
        const initialState = get(nodes);
        undo();
        expect(get(nodes)).toEqual(initialState);
        expect(get(canUndo)).toBe(false);
    });

    it('redo does nothing when at end of history', () => {
        nodes.set([{ id: 'node1', position: { x: 0, y: 0 }, data: {} }]);
        pushHistory();
        vi.advanceTimersByTime(400);

        const currentState = get(nodes);
        redo();
        expect(get(nodes)).toEqual(currentState);
    });

    it('new changes after undo clears redo stack', async () => {
        // State 1
        nodes.set([{ id: 'node1', position: { x: 0, y: 0 }, data: {} }]);
        pushHistory();
        vi.advanceTimersByTime(400);

        // State 2
        nodes.set([
            { id: 'node1', position: { x: 0, y: 0 }, data: {} },
            { id: 'node2', position: { x: 100, y: 0 }, data: {} },
        ]);
        pushHistory();
        vi.advanceTimersByTime(400);

        // Undo to state 1
        undo();
        expect(get(canRedo)).toBe(true);

        // Make a new change (state 3)
        nodes.set([{ id: 'node3', position: { x: 50, y: 50 }, data: {} }]);
        pushHistory();
        vi.advanceTimersByTime(400);

        // Redo should now be disabled (state 2 is gone)
        expect(get(canRedo)).toBe(false);
    });

    it('multiple undos work correctly', async () => {
        // State 1
        nodes.set([{ id: 'node1', position: { x: 0, y: 0 }, data: {} }]);
        pushHistory();
        vi.advanceTimersByTime(400);

        // State 2
        nodes.set([{ id: 'node2', position: { x: 0, y: 0 }, data: {} }]);
        pushHistory();
        vi.advanceTimersByTime(400);

        // State 3
        nodes.set([{ id: 'node3', position: { x: 0, y: 0 }, data: {} }]);
        pushHistory();
        vi.advanceTimersByTime(400);

        // Undo twice to get back to state 1
        undo(); // Back to state 2
        undo(); // Back to state 1

        expect(get(nodes)[0].id).toBe('node1');
    });

    it('debounces rapid pushHistory calls', async () => {
        // Rapid changes (like dragging)
        nodes.set([{ id: 'node1', position: { x: 0, y: 0 }, data: {} }]);
        pushHistory();
        nodes.set([{ id: 'node1', position: { x: 10, y: 10 }, data: {} }]);
        pushHistory();
        nodes.set([{ id: 'node1', position: { x: 20, y: 20 }, data: {} }]);
        pushHistory();

        // Only advance 100ms (less than 300ms debounce)
        vi.advanceTimersByTime(100);
        expect(get(canUndo)).toBe(false);

        // Complete the debounce - only the last state should be recorded
        vi.advanceTimersByTime(300);
        expect(get(canUndo)).toBe(true);

        // Undo should go back to initial empty state, not intermediate states
        undo();
        expect(get(nodes)).toEqual([]);
    });
});

