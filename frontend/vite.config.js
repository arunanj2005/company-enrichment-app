import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/enrichInput': 'http://localhost:3001',
      '/results': 'http://localhost:3001',
      '/enrichBatch': 'http://localhost:3001',
    }
  }
});
