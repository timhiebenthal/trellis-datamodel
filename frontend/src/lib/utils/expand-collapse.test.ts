import { describe, it, expect } from 'vitest';
import { nextExpandCollapseState } from './expand-collapse';

describe('nextExpandCollapseState', () => {
    const entity = (id: string, collapsed: boolean) =>
        ({ id, type: 'entity', data: { collapsed } });
    const group = (id: string, collapsed: boolean) =>
        ({ id, type: 'group', data: { collapsed } });

    it('expands when any entity is collapsed', () => {
        expect(nextExpandCollapseState([
            group('g', false),
            entity('a', false),
            entity('b', true),
        ])).toBe(true);
    });

    it('collapses when every entity is expanded', () => {
        expect(nextExpandCollapseState([
            group('g', false),
            entity('a', false),
            entity('b', false),
        ])).toBe(false);
    });

    it('expands when only group nodes exist (nothing to see)', () => {
        expect(nextExpandCollapseState([group('g', false)])).toBe(true);
    });

    it('treats missing collapsed flag as expanded', () => {
        expect(nextExpandCollapseState([
            { id: 'a', type: 'entity', data: {} },
        ])).toBe(false);
    });
});
