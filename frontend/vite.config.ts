/// <reference types="vitest/config" />
import { defineConfig } from 'vite';

// `root` fijo: sin él, Vite toma el directorio de trabajo y `fs.allow: ['.']` se resolvería contra
// la raíz del repositorio si el servidor se arranca desde allí, con novelas/ dentro (RF-43).
const root = import.meta.dirname;
const servidor = { host: 'localhost', port: 5173, strictPort: true } as const;

export default defineConfig({
  root,
  // Rutas por hash: sin fallback de SPA, una ruta desconocida es un 404 y no index.html.
  appType: 'mpa',
  server: { ...servidor, fs: { strict: true, allow: ['.'] } },
  preview: servidor,
  test: {
    include: ['src/**/*.test.ts', 'scripts/**/*.test.ts'],
    environment: 'jsdom',
  },
});
