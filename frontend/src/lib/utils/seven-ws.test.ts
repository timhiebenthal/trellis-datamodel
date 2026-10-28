import { describe, it, expect } from 'vitest';
import { SEVEN_W_TYPES, SEVEN_W_LABELS, SEVEN_W_ICONS, SEVEN_W_BADGE_CLASSES } from './seven-ws';

describe('seven-ws constants', () => {
    it('lists the seven annotation types in display order', () => {
        expect(SEVEN_W_TYPES).toEqual(['who', 'what', 'when', 'where', 'how', 'why', 'how_many']);
    });

    it('defines a label, icon and badge class for every type', () => {
        for (const type of SEVEN_W_TYPES) {
            expect(SEVEN_W_LABELS[type]).toBeTruthy();
            expect(SEVEN_W_ICONS[type]).toMatch(/^lucide:/);
            expect(SEVEN_W_BADGE_CLASSES[type]).toMatch(/^bg-/);
        }
        expect(SEVEN_W_LABELS.how_many).toBe('How Many');
    });
});
