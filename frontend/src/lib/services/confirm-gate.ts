/**
 * Turns a confirm/cancel dialog into an awaitable decision: `request()`
 * returns a promise that the dialog's buttons settle via `settle(true|false)`.
 * Settling with no pending request is a no-op. A new `request()` while one is
 * still pending cancels the earlier one (it resolves `false`) so it never hangs.
 */
export function createConfirmGate() {
    let resolve: ((value: boolean) => void) | null = null;
    return {
        request(): Promise<boolean> {
            resolve?.(false);
            return new Promise((r) => {
                resolve = r;
            });
        },
        settle(value: boolean) {
            if (resolve) {
                resolve(value);
                resolve = null;
            }
        },
    };
}
