// @vitest-environment node
// package.json contra RF-44: dos dependencias de ejecución y ningún cliente de modelos (AGENTS.md,
// «Nunca»).
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const FRONTEND = path.resolve(import.meta.dirname, '..');
const paquete = JSON.parse(fs.readFileSync(path.join(FRONTEND, 'package.json'), 'utf8')) as {
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
};

const PROHIBIDO = /^(@anthropic-ai\/.*|openai|@google\/generative-ai|langchain|@langchain\/.*|ai)$/;

describe('dependencias (CA-44)', () => {
  it('las de ejecución son exactamente three y markdown-it', () => {
    expect(Object.keys(paquete.dependencies ?? {}).sort()).toEqual(['markdown-it', 'three']);
  });

  it('ninguna es un SDK o cliente de un proveedor de modelos', () => {
    const todas = Object.keys({ ...paquete.dependencies, ...paquete.devDependencies });
    expect(todas.filter((nombre) => PROHIBIDO.test(nombre))).toEqual([]);
  });
});

describe('imágenes versionadas (CA-60)', () => {
  it('solo logo.png, favicon.png y las referencias de visual.spec.ts', () => {
    const versionados = execFileSync('git', ['ls-files', '--', '.'], { cwd: FRONTEND, encoding: 'utf8' })
      .split('\n')
      .filter((f) => /\.(png|jpe?g|webp|gif|svg|ico)$/i.test(f));
    const permitidas = (f: string): boolean =>
      ['src/shared/marca/logo.png', 'public/favicon.png'].includes(f) ||
      f.startsWith('e2e/visual.spec.ts-snapshots/');
    expect(versionados.filter((f) => !permitidas(f))).toEqual([]);
  });
});
