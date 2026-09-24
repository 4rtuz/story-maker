// @vitest-environment node
// CA-40 (parte del presupuesto), RNF-01, RNF-02 y RNF-20 sobre dist/ de fixture, generados en el
// directorio temporal: el script se ejecuta como lo ejecuta CI. 1 KB = 1 000 bytes (D52).
import { spawnSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';

const SCRIPT = path.join(import.meta.dirname, 'presupuesto.mjs');
const temporales: string[] = [];
afterAll(() => temporales.forEach((d) => fs.rmSync(d, { recursive: true, force: true })));

interface Fixture {
  inicial?: Record<string, number>; // bytes aleatorios: su gzip ocupa casi lo mismo
  precargado?: Record<string, number>;
  diferido?: Record<string, number>;
  woff2?: number;
  css?: number;
  logo?: number;
  favicon?: number;
}

function dist(f: Fixture): string {
  const raiz = fs.mkdtempSync(path.join(os.tmpdir(), 'dist-'));
  temporales.push(raiz);
  fs.mkdirSync(path.join(raiz, 'assets'));
  const escribir = (nombre: string, bytes: number) => fs.writeFileSync(path.join(raiz, nombre), randomBytes(bytes));
  const etiquetas: string[] = [];
  for (const [nombre, bytes] of Object.entries(f.inicial ?? { 'index-a.js': 1_000 })) {
    escribir(`assets/${nombre}`, bytes);
    etiquetas.push(`<script type="module" crossorigin src="/assets/${nombre}"></script>`);
  }
  for (const [nombre, bytes] of Object.entries(f.precargado ?? {})) {
    escribir(`assets/${nombre}`, bytes);
    etiquetas.push(`<link rel="modulepreload" crossorigin href="/assets/${nombre}">`);
  }
  for (const [nombre, bytes] of Object.entries(f.diferido ?? { 'escena-c.js': 1_000 })) escribir(`assets/${nombre}`, bytes);
  escribir('assets/outfit-800-d.woff2', f.woff2 ?? 14_000);
  escribir('assets/index-e.css', f.css ?? 1_000);
  etiquetas.push('<link rel="stylesheet" crossorigin href="/assets/index-e.css">');
  escribir('assets/logo-1a2b.png', f.logo ?? 68_000);
  escribir('favicon.png', f.favicon ?? 4_000);
  fs.writeFileSync(path.join(raiz, 'index.html'), `<!doctype html><head>${etiquetas.join('')}</head>`);
  return raiz;
}

function presupuesto(raiz: string, lectura = 'opcional') {
  const r = spawnSync(process.execPath, [SCRIPT, raiz, `--lectura=${lectura}`], { encoding: 'utf8' });
  return { codigo: r.status, salida: r.stdout + r.stderr };
}

describe('presupuestos (CA-40)', () => {
  it('un dist dentro de todos los presupuestos sale con 0 (control)', () => {
    expect(presupuesto(dist({})).codigo).toBe(0);
  });

  it('un chunk inicial de más de 100 000 bytes gzip sale con distinto de 0', () => {
    const { codigo, salida } = presupuesto(dist({ inicial: { 'index-a.js': 101_000 } }));
    expect(codigo).not.toBe(0);
    expect(salida).toMatch(/inicial/i);
  });

  it('los modulepreload cuentan como carga inicial (VER-15)', () => {
    const r = presupuesto(dist({ inicial: { 'index-a.js': 60_000 }, precargado: { 'vendor-b.js': 60_000 } }));
    expect(r.codigo).not.toBe(0);
    expect(r.salida).toMatch(/inicial/i);
  });

  it('el chunk de Lectura de más de 300 000 bytes gzip sale con distinto de 0', () => {
    const r = presupuesto(dist({ diferido: { 'escena-c.js': 200_000, 'three-f.js': 110_000 } }));
    expect(r.codigo).not.toBe(0);
    expect(r.salida).toMatch(/lectura/i);
  });

  it('un WOFF2 de más de 60 000 bytes sale con distinto de 0', () => {
    expect(presupuesto(dist({ woff2: 60_001 })).codigo).not.toBe(0);
  });

  it('el CSS de más de 20 000 bytes gzip sale con distinto de 0', () => {
    expect(presupuesto(dist({ css: 21_000 })).codigo).not.toBe(0);
  });

  it('logo con hash y favicon: 80 001 bytes fallan y 80 000 pasan (D52)', () => {
    const excede = presupuesto(dist({ logo: 68_000, favicon: 12_001 }));
    expect(excede.codigo).not.toBe(0);
    expect(excede.salida).toMatch(/imágenes/i);
    expect(presupuesto(dist({ logo: 68_000, favicon: 12_000 })).codigo).toBe(0);
  });

  it('exigido, sin chunk de Lectura sale con distinto de 0 y lo nombra (VER-14)', () => {
    const r = presupuesto(dist({ diferido: {} }), 'exigida');
    expect(r.codigo).not.toBe(0);
    expect(r.salida).toMatch(/no hay chunk de Lectura/);
    expect(presupuesto(dist({ diferido: {} }), 'opcional').codigo).toBe(0);
  });
});
