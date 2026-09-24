// @vitest-environment node
// package.json contra RF-44: dos dependencias de ejecución y ningún cliente de modelos (AGENTS.md,
// «Nunca»).
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
