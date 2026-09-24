// @vitest-environment node
// RF-02: los tipos de las respuestas salen de esquema.gen.ts. Una declaración a mano con el nombre
// de un esquema del OpenAPI es una copia que deriva en silencio cuando cambia el backend.
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const FRONTEND = path.resolve(import.meta.dirname, '..');
const openapi = JSON.parse(
  fs.readFileSync(path.join(FRONTEND, '..', 'backend', 'api', 'openapi.json'), 'utf8'),
) as { components: { schemas: Record<string, unknown> } };
const ESQUEMAS = new Set(Object.keys(openapi.components.schemas));

/** `fichero: Nombre` por cada `interface` o `type` con el nombre de un esquema. */
function copias(directorio: string): string[] {
  return fs
    .readdirSync(directorio, { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.ts') && path.basename(f) !== 'esquema.gen.ts')
    .flatMap((f) => {
      const texto = fs.readFileSync(path.join(directorio, f), 'utf8');
      return [...texto.matchAll(/\b(?:interface|type)\s+([A-Za-z_$][\w$]*)/g)]
        .map((m) => m[1] ?? '')
        .filter((nombre) => ESQUEMAS.has(nombre))
        .map((nombre) => `${f}: ${nombre}`);
    });
}

describe('tipos de la API (CA-02)', () => {
  it('detecta una copia a mano (control positivo)', () => {
    expect(copias(path.join(FRONTEND, 'test', 'fixtures', 'contrato'))).toEqual([
      'copia.ts: Checkpoint',
    ]);
  });

  it('src/ no declara ningún esquema del OpenAPI fuera de esquema.gen.ts', () => {
    expect(copias(path.join(FRONTEND, 'src'))).toEqual([]);
  });

  it('esquema.gen.ts existe y declara los esquemas', () => {
    const generado = fs.readFileSync(path.join(FRONTEND, 'src/shared/api/esquema.gen.ts'), 'utf8');
    for (const nombre of ['Config', 'Escaleta', 'Checkpoint', 'TramoDeLog', 'Manifest']) {
      expect(generado).toContain(`${nombre}: {`);
    }
  });
});
