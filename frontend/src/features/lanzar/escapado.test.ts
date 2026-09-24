// @vitest-environment node
// CA-14 (RF-14, D44): la idea entre comillas simples es un único argumento que bash devuelve igual,
// con y sin expansión del historial, sin ejecutar nada. Todas las ideas van en un solo proceso de
// bash por modo, por stdin y separadas por NUL, que ninguna idea contiene. Sin bash en el PATH el
// test falla con un mensaje que lo nombra: no se salta (D36, VER-16).
import { spawnSync } from 'node:child_process';
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import { entrecomillar, ordenNovelaNueva } from './orden';

const FIJOS = [
  "'",
  "''",
  "it's",
  "'inicio",
  "fin'",
  'fin\\',
  'a\\\nb',
  '$(id)',
  '`id`',
  '\\"',
  '!!',
  'ñ ü €',
  'una idea que termina en salto de línea\n',
  '$HOME ${HOME} $((1+1))',
];

const TROZO = fc.oneof(
  fc.constantFrom("'", '"', '\\', '$', '$(id)', '`', '`id`', '!', '!!', '\n', 'á', 'ñ', 'Ñ', 'ü', '€', ' ', '\t'),
  fc.string({ unit: 'grapheme', minLength: 1 }).filter((s) => !s.includes('\0')),
);
const IDEA = fc.array(TROZO, { minLength: 1, maxLength: 12 }).map((t) => t.join(''));

/** El argumento de --idea tal como sale en la orden, sin flags opcionales detrás. */
function argumento(idea: string): string {
  const orden = ordenNovelaNueva({ slug: 'nueva-prueba', idea, capitulos: '', palabras: '' });
  const prefijo = '/novela-nueva nueva-prueba --idea ';
  expect(orden.startsWith(prefijo)).toBe(true);
  return orden.slice(prefijo.length);
}

function bash(ideas: string[], prologo: string): string[] {
  const guion = [prologo, ...ideas.map((i) => `printf %s ${argumento(i)}; printf '\\0'`)].join('\n');
  const r = spawnSync('bash', ['-s'], { input: guion, encoding: 'utf8' });
  if (r.error) throw new Error(`bash no está en el PATH: CA-14 lo necesita, también en Windows con Git Bash (D36). ${r.error.message}`);
  expect(r.stderr).toBe('');
  expect(r.status).toBe(0);
  return r.stdout.split('\0').slice(0, -1);
}

describe('la idea entre comillas simples (CA-14)', () => {
  const ideas = [...FIJOS, ...fc.sample(IDEA, { numRuns: 240, seed: 20260924 })];

  it('entrecomilla y sustituye cada comilla simple', () => {
    expect(entrecomillar("it's")).toBe("'it'\\''s'");
    expect(ideas.length).toBeGreaterThanOrEqual(200);
  });

  it.each([
    ['tal cual', ''],
    ['con set -H', 'set -H'],
  ])('bash devuelve cada idea exacta, %s', (_, prologo) => {
    expect(bash(ideas, prologo)).toEqual(ideas);
  }, 60_000);
});
