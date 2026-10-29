import { describe, it, expect } from 'vitest';
import { createConfirmGate } from './confirm-gate';

describe('createConfirmGate', () => {
    it('resolves the pending request with the settled value', async () => {
        const gate = createConfirmGate();
        const confirmed = gate.request();
        gate.settle(true);
        await expect(confirmed).resolves.toBe(true);

        const cancelled = gate.request();
        gate.settle(false);
        await expect(cancelled).resolves.toBe(false);
    });

    it('ignores settles with no pending request', async () => {
        const gate = createConfirmGate();
        gate.settle(true);

        const decision = gate.request();
        gate.settle(false);
        gate.settle(true);
        await expect(decision).resolves.toBe(false);
    });

    it('cancels a pending request when a new one is made, so it never hangs', async () => {
        const gate = createConfirmGate();
        const first = gate.request();
        const second = gate.request();
        await expect(first).resolves.toBe(false);

        gate.settle(true);
        await expect(second).resolves.toBe(true);
    });
});
