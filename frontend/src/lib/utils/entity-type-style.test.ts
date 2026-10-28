import { describe, it, expect } from 'vitest';
import { getEntityTypeStyle } from './entity-type-style';

describe('getEntityTypeStyle', () => {
    it('styles dimension green with the list icon', () => {
        const s = getEntityTypeStyle('dimension');
        expect(s.icon).toBe('lucide:list');
        expect(s.badge).toContain('bg-green-100');
        expect(s.badge).toContain('text-green-700');
        expect(s.iconClass).toBe('text-green-600');
        expect(s.label).toBe('Dimension');
    });

    it('styles fact blue with the bar-chart icon', () => {
        const s = getEntityTypeStyle('fact');
        expect(s.icon).toBe('lucide:bar-chart-3');
        expect(s.badge).toContain('bg-blue-100');
        expect(s.badge).toContain('text-blue-700');
        expect(s.iconClass).toBe('text-blue-600');
        expect(s.label).toBe('Fact');
    });

    it('styles the generic entity type neutral but keeps its label', () => {
        const s = getEntityTypeStyle('entity');
        expect(s.icon).toBe('lucide:circle-dashed');
        expect(s.badge).toContain('bg-gray-100');
        expect(s.label).toBe('Entity');
    });

    it.each([['unclassified'], [undefined], [null], ['bogus']])('falls back to neutral unclassified for %s', (t) => {
        const s = getEntityTypeStyle(t as string | null | undefined);
        expect(s.icon).toBe('lucide:circle-dashed');
        expect(s.badge).toContain('bg-gray-100');
        expect(s.iconClass).toBe('text-gray-500');
        expect(s.label).toBe('Unclassified');
    });
});
