// @vitest-environment node
// Las reglas de eslint.config.js sobre ficheros de fixture con usos prohibidos. Cada fixture se
// lintea como si estuviera en la ruta de `src/` que le toca: las reglas dependen de la ruta, y la
// carpeta de fixtures queda fuera de `eslint .` para que `npm run lint` salga limpio (VER-7).
import fs from 'node:fs';
import path from 'node:path';
import { ESLint, type Linter } from 'eslint';
import { describe, expect, it } from 'vitest';

const FRONTEND = path.resolve(import.meta.dirname, '..');
const FIXTURES = path.join(FRONTEND, 'test', 'fixtures', 'lint');
const eslint = new ESLint({ cwd: FRONTEND });

async function errores(fixture: string, como: string): Promise<Linter.LintMessage[]> {
  const codigo = fs.readFileSync(path.join(FIXTURES, fixture), 'utf8');
  const [resultado] = await eslint.lintText(codigo, { filePath: path.join(FRONTEND, como) });
  return resultado?.messages.filter((m) => m.severity === 2) ?? [];
}

describe('imports de fuera de src/ (CA-43)', () => {
  it.each([
    ['import-novelas.ts', 'src/x.ts'],
    ['import-backend.ts', 'src/x.ts'],
  ])('%s es error', async (fixture, como) => {
    expect(await errores(fixture, como)).not.toEqual([]);
  });

  it('un import dentro de src/ no lo es (control positivo)', async () => {
    expect(await errores('limpio.ts', 'src/app/x.ts')).toEqual([]);
  });
});

describe('HTML sin sanear (no-unsanitized)', () => {
  it('una asignación a innerHTML es error', async () => {
    const mensajes = await errores('inner-html.ts', 'src/app/x.ts');
    expect(mensajes.map((m) => m.ruleId)).toContain('no-unsanitized/property');
  });
});

describe('red solo desde src/shared/api/ (CA-03, VER-12)', () => {
  it.each([
    'red-fetch.ts',
    'red-xhr.ts',
    'red-websocket.ts',
    'red-eventsource.ts',
    'red-window-fetch.ts',
    'red-global-fetch.ts',
    'red-beacon.ts',
  ])('%s fuera de src/shared/api/ es error', async (fixture) => {
    expect(await errores(fixture, 'src/features/progreso/x.ts')).not.toEqual([]);
  });

  it('dentro de src/shared/api/ no lo es (control positivo)', async () => {
    expect(await errores('red-fetch.ts', 'src/shared/api/x.ts')).toEqual([]);
  });
});

describe('logo.png reservado a logo.ts (CA-51, parte estática)', () => {
  it('importarlo fuera de logo.ts es error', async () => {
    expect(await errores('import-logo.ts', 'src/app/x.ts')).not.toEqual([]);
  });

  it('desde logo.ts no lo es (control positivo)', async () => {
    expect(await errores('logo-permitido.ts', 'src/shared/marca/logo.ts')).toEqual([]);
  });
});
