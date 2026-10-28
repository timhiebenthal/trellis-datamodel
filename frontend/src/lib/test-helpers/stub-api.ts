import { afterEach, beforeEach, vi } from 'vitest';

/**
 * Stubs global `fetch` at a single boundary with a route table keyed by
 * `"METHOD /path?query"` (origin ignored). Any request without a route throws
 * and is also reported by `afterEach`, so a swallowed error cannot hide it.
 */
export type RouteReply =
    | { status?: number; json?: unknown; text?: string; headers?: Record<string, string> }
    | { networkError: Error };

export interface SentRequest {
    method: string;
    path: string;
    /** Parsed JSON request body, if one was sent. */
    body: any;
}

export function useApiStub() {
    let routes: Record<string, RouteReply> = {};
    let sent: SentRequest[] = [];
    let unrouted: string[] = [];

    beforeEach(() => {
        routes = {};
        sent = [];
        unrouted = [];
        vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
            const url = new URL(String(input), 'http://localhost');
            const method = String(init?.method ?? 'GET').toUpperCase();
            const path = `${url.pathname}${url.search}`;
            const key = `${method} ${path}`;
            sent.push({
                method,
                path,
                body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined,
            });
            const reply = routes[key];
            if (!reply) {
                unrouted.push(key);
                throw new Error(`Unrouted request in test: ${key}`);
            }
            if ('networkError' in reply) throw reply.networkError;
            const body = reply.text ?? (reply.json === undefined ? '' : JSON.stringify(reply.json));
            return new Response(body, {
                status: reply.status ?? 200,
                headers: reply.headers,
            });
        });
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        if (unrouted.length > 0) {
            throw new Error(`Unrouted requests: ${unrouted.join(', ')}`);
        }
    });

    return {
        /** Define the replies for this test, e.g. `{ 'GET /api/data-model': { json: model } }`. */
        route(table: Record<string, RouteReply>) {
            routes = { ...routes, ...table };
        },
        /** Requests the code under test sent, in order. */
        get sent(): SentRequest[] {
            return sent;
        },
    };
}
