import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        // Loopback only: the dev server proxies the unauthenticated API. Set
        // VITE_DEV_HOST=true for devcontainers and port-forwarding setups that need it.
        host: process.env.VITE_DEV_HOST === 'true' ? true : 'localhost',
        port: 5173,
        strictPort: true,
        // Keep frontend code using relative `/api/...` while developing (no env var flipping).
        proxy: {
            '/api': {
                // Trellis backend default: http://localhost:8089
                // Override via: VITE_DEV_API_TARGET=http://localhost:8089
                target: process.env.VITE_DEV_API_TARGET ?? 'http://localhost:8089',
                changeOrigin: true,
            },
        },
    },
    // Ensure we always resolve browser-ready builds (Svelte defaults to server-first if unset)
    resolve: {
        conditions: ['browser'],
    },
    test: {
        include: ['src/**/*.{test,spec}.{js,ts}'],
        environment: 'jsdom',
        setupFiles: ['./tests/vitest-setup.ts'],
        // Heavy jsdom component tests (EntityDetailModal, SevenWsForm) exceed the 5s
        // default when the full suite runs in parallel.
        testTimeout: 20000,
        coverage: {
            provider: 'v8',
            reporter: ['text-summary', 'lcov'],
            include: ['src/**/*.{ts,svelte}'],
            exclude: ['src/**/*.{test,spec}.{js,ts}'],
        },
    }
});
