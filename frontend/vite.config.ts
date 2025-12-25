import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        // Makes the dev server reachable from WSL/devcontainers and port-forwarding setups.
        host: true,
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
    test: {
        include: ['src/**/*.{test,spec}.{js,ts}']
    }
});
