import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/status': 'http://localhost:8770',
      '/midi': 'http://localhost:8770',
      '/session': 'http://localhost:8770',
      '/patch': 'http://localhost:8770',
      '/ws': {
        target: 'ws://localhost:8770',
        ws: true,
      },
    },
  },
});
