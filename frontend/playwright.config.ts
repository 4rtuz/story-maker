// e2e del panel (spec 0004 §13): la API real sobre los workspaces sintéticos de panel.py y el build
// servido con vite preview en localhost:5173, en Chromium y Firefox. Ningún test llama a un modelo.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

/** Donde e2e/preparar.ts genera los workspaces; la API lee de aquí en cada petición. */
export const NOVELAS = process.env.PANEL_NOVELAS_DIR ?? path.join(os.tmpdir(), 'panel-e2e-novelas');
fs.mkdirSync(NOVELAS, { recursive: true }); // la API arranca antes que la preparación

const CI = Boolean(process.env.CI);
const pantalla = { viewport: { width: 1440, height: 900 } };

export default defineConfig({
  testDir: 'e2e',
  globalSetup: './e2e/preparar.ts',
  forbidOnly: CI,
  retries: 0,
  reporter: CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: { baseURL: 'http://localhost:5173', locale: 'es-ES', timezoneId: 'Europe/Madrid', trace: 'retain-on-failure' },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], ...pantalla } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'], ...pantalla } },
  ],
  webServer: [
    {
      command: 'uv run uvicorn api.main:app --host 127.0.0.1 --port 8000',
      cwd: path.join(import.meta.dirname, '..', 'backend'),
      url: 'http://127.0.0.1:8000/novelas',
      env: { NOVELAS_DIR: NOVELAS },
      reuseExistingServer: !CI,
      timeout: 120_000,
    },
    {
      command: 'npm run build && npm run preview',
      url: 'http://localhost:5173',
      reuseExistingServer: !CI,
      timeout: 180_000,
    },
  ],
});
