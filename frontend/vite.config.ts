import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
    plugins: [sveltekit()],
    optimizeDeps: {
        include: ['@dagrejs/dagre', '@dagrejs/graphlib'],
        esbuildOptions: {
            // Transform CommonJS to ESM
            target: 'esnext',
            format: 'esm'
        }
    },
    ssr: {
        noExternal: ['@dagrejs/dagre', '@dagrejs/graphlib']
    },
    test: {
        include: ['src/**/*.{test,spec}.{js,ts}']
    }
});
