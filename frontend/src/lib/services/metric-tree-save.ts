import type { MetricTreeFile } from '$lib/types';
import { saveMetricTree } from '$lib/api';

/**
 * Debounced autosave for the metric tree.
 *
 * Deliberately a second, small service rather than a reuse of `AutoSaveService`:
 * that one hardcodes the entity-canvas serializer and endpoint. The semantics are
 * copied on purpose - 400 ms debounce, in-flight coalescing, a baseline comparison
 * so a no-op edit never posts, and a synchronous flush for unload - so the two
 * canvases behave the same way to a user.
 */

export interface MetricTreeSaveState {
    isSaving: boolean;
    warnings: string[];
    error: string | null;
}

export interface MetricTreeSaveOptions {
    /** Quiet period before a pending edit is sent. */
    debounceMs?: number;
    /**
     * Gate. The backend rejects a draft without an expression with 422, so the
     * page hands in a predicate that says whether the document is saveable. A
     * gated payload is never posted and never advances the baseline.
     */
    canSave?: (payload: MetricTreeFile) => boolean;
    onStateChange?: (state: MetricTreeSaveState) => void;
}

export class MetricTreeSaveService {
    private debounceMs: number;
    private canSave: (payload: MetricTreeFile) => boolean;
    private onStateChange?: (state: MetricTreeSaveState) => void;

    private pendingTimeout: ReturnType<typeof setTimeout> | null = null;
    /** State waiting out the debounce. */
    private queuedState: string | null = null;
    private queuedPayload: MetricTreeFile | null = null;
    /** State currently being written. */
    private inFlightState: string | null = null;
    private inFlightPromise: Promise<void> | null = null;
    private lastSavedState = '';
    private saving = false;
    private warnings: string[] = [];
    private error: string | null = null;

    constructor(options: MetricTreeSaveOptions = {}) {
        this.debounceMs = options.debounceMs ?? 400;
        this.canSave = options.canSave ?? (() => true);
        this.onStateChange = options.onStateChange;
    }

    /** Treat the just-loaded document as saved, so loading never posts. */
    initializeBaseline(payload: MetricTreeFile): void {
        this.clearTimer();
        this.lastSavedState = serialize(payload);
        this.queuedState = null;
        this.queuedPayload = null;
        this.inFlightState = null;
        this.inFlightPromise = null;
        this.saving = false;
        this.error = null;
        this.warnings = [];
        this.emit();
    }

    /** Queue a debounced save. Repeated calls inside the window collapse to the last payload. */
    save(payload: MetricTreeFile): void {
        const state = serialize(payload);

        if (!this.canSave(payload)) {
            // Paused, not failed: drop whatever was queued so a stale document
            // cannot be written after the edit that made this one invalid.
            this.clearTimer();
            this.queuedState = null;
            this.queuedPayload = null;
            this.saving = this.inFlightState !== null;
            this.emit();
            return;
        }

        if (state === this.lastSavedState || state === this.queuedState || state === this.inFlightState) {
            return;
        }

        this.clearTimer();
        this.queuedState = state;
        this.queuedPayload = snapshot(payload);
        this.saving = true;
        this.emit();

        this.pendingTimeout = setTimeout(() => {
            this.pendingTimeout = null;
            const queuedPayload = this.queuedPayload;
            const queuedState = this.queuedState;
            this.queuedState = null;
            this.queuedPayload = null;

            if (queuedPayload && queuedState) {
                void this.persist(queuedPayload, queuedState);
            }
        }, this.debounceMs);
    }

    /** Save immediately, skipping the debounce. */
    saveNow(payload: MetricTreeFile): Promise<void> {
        this.clearTimer();

        if (!this.canSave(payload)) {
            this.saving = this.inFlightState !== null;
            this.emit();
            return Promise.resolve();
        }

        const state = serialize(payload);
        if (state === this.lastSavedState) return this.inFlightPromise ?? Promise.resolve();
        if (state === this.inFlightState) return this.inFlightPromise ?? Promise.resolve();

        this.queuedState = null;
        this.queuedPayload = null;
        return this.persist(snapshot(payload), state);
    }

    /**
     * Send anything pending right now. Used on unload, where the debounce would
     * otherwise lose the last edit.
     */
    async flushSync(payload: MetricTreeFile): Promise<void> {
        this.clearTimer();

        if (!this.canSave(payload)) return;

        const state = serialize(payload);
        if (state === this.lastSavedState) return;
        if (state === this.inFlightState) {
            await this.inFlightPromise;
            return;
        }

        this.queuedState = null;
        this.queuedPayload = null;
        await this.persist(snapshot(payload), state);
    }

    /** True when the payload differs from what the server last accepted. */
    hasUnsavedChanges(payload: MetricTreeFile): boolean {
        const baseline = this.inFlightState ?? this.lastSavedState;
        return baseline !== '' && baseline !== serialize(payload);
    }

    /** A save is pending, in flight, or currently writing. */
    isSavingActive(): boolean {
        return this.saving || this.pendingTimeout !== null || this.inFlightState !== null;
    }

    /** Same as `isSavingActive()`, for callers that read a plain flag. */
    get isSaving(): boolean {
        return this.isSavingActive();
    }

    getWarnings(): string[] {
        return [...this.warnings];
    }

    getError(): string | null {
        return this.error;
    }

    private async persist(payload: MetricTreeFile, state: string): Promise<void> {
        this.inFlightState = state;
        this.saving = true;
        this.emit();

        const request = (async () => {
            try {
                const result = await saveMetricTree(payload);
                this.lastSavedState = state;
                this.warnings = result?.warnings ?? [];
                this.error = null;
            } catch (e) {
                // Keep the baseline where it was: the edit stays unsaved, stays on
                // screen, and the next attempt retries it.
                this.error = e instanceof Error ? e.message : String(e);
            } finally {
                this.inFlightState = null;
                this.inFlightPromise = null;
            }
        })();

        this.inFlightPromise = request;
        await request;

        // A change that arrived while this request was in flight is coalesced into
        // one follow-up save of the newest payload.
        const queuedState = this.queuedState;
        const queuedPayload = this.queuedPayload;
        if (queuedPayload && queuedState && queuedState !== this.lastSavedState) {
            this.queuedState = null;
            this.queuedPayload = null;
            await this.persist(queuedPayload, queuedState);
            return;
        }

        this.saving = this.pendingTimeout !== null || this.inFlightState !== null;
        this.emit();
    }

    private clearTimer(): void {
        if (this.pendingTimeout) {
            clearTimeout(this.pendingTimeout);
            this.pendingTimeout = null;
        }
    }

    private emit(): void {
        this.onStateChange?.({
            isSaving: this.isSavingActive(),
            warnings: [...this.warnings],
            error: this.error,
        });
    }
}

function serialize(payload: MetricTreeFile): string {
    return JSON.stringify(payload);
}

/** Freeze the payload: later edits to the live document must not leak into a queued save. */
function snapshot(payload: MetricTreeFile): MetricTreeFile {
    return JSON.parse(JSON.stringify(payload)) as MetricTreeFile;
}
