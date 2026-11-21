import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// `npm run dev` proxies Mopidy (WebSocket + Melody API) from a running server:
//   MOPIDY_URL=http://<mopidy-host>:6680 npm run dev
const target = process.env.MOPIDY_URL || 'http://localhost:6680';

export default defineConfig({
  plugins: [svelte()],
  base: './',
  build: {
    outDir: '../src/mopidy_melody/www',
    emptyOutDir: true,
    target: 'es2020',
  },
  server: {
    proxy: {
      '/mopidy': { target, ws: true, changeOrigin: true },
      '/api': { target: `${target}/melody`, changeOrigin: true },
    },
  },
});
