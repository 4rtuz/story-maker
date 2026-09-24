// @vitest-environment node
// CA-47 y RNF-19: el contraste de cada par declarado, recalculado desde tokens.css en cada
// ejecución, con las transparencias compuestas sobre su fondo antes de linealizar (VER-18).
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { lectorDeCss, type Rgba } from './lector-de-tokens';
import { PARES, UMBRALES } from './pares';

const TOKENS = fs.readFileSync(path.join(import.meta.dirname, 'tokens.css'), 'utf8');
const leer = lectorDeCss(TOKENS);

const lineal = (c: number): number => {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};
const luminancia = ({ r, g, b }: Rgba): number =>
  0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b);
// En sRGB y redondeado a 8 bits por canal, como pinta el navegador; después se linealiza.
const canal = (arriba: number, abajo: number, a: number): number =>
  Math.round(arriba * a + abajo * (1 - a));
const componer = (arriba: Rgba, abajo: Rgba): Rgba => ({
  r: canal(arriba.r, abajo.r, arriba.a),
  g: canal(arriba.g, abajo.g, arriba.a),
  b: canal(arriba.b, abajo.b, arriba.a),
  a: 1,
});

function contraste(primerPlano: Rgba, fondo: Rgba): number {
  const [clara, oscura] = [luminancia(primerPlano), luminancia(fondo)].sort((x, y) => y - x);
  return ((clara ?? 0) + 0.05) / ((oscura ?? 0) + 0.05);
}

function contrasteDe(css: (rol: string) => Rgba, par: (typeof PARES)[number]): number {
  const fondo = par.sobre ? componer(css(par.fondo), css(par.sobre)) : css(par.fondo);
  return contraste(css(par.primerPlano), fondo);
}

describe('cálculo del contraste (control conocido, VER-18)', () => {
  const control = lectorDeCss(`:root {
    --q-tinta: #1F2937; --q-papel: #FFFFFF; --q-marron: #7C3A12; --q-pizarra: #2D3748;
    --q-vivo: #F97316; --q-velo: color-mix(in srgb, var(--q-papel) 15%, transparent);
  }`);
  it.each([
    [{ primerPlano: '--q-tinta', fondo: '--q-papel' }, 14.68],
    [{ primerPlano: '--q-papel', fondo: '--q-velo', sobre: '--q-marron' }, 5.78],
    [{ primerPlano: '--q-vivo', fondo: '--q-pizarra' }, 4.28],
  ])('%o da %f', (par, esperado) => {
    const valor = contrasteDe(control, { ...par, tipo: 'texto' });
    expect(Math.abs(valor - esperado)).toBeLessThanOrEqual(0.02);
  });
});

describe('pares de tokens.css (CA-47)', () => {
  it.each(PARES.map((par) => [`${par.primerPlano} sobre ${par.sobre ?? par.fondo}`, par] as const))(
    '%s cumple su umbral',
    (_, par) => {
      expect(contrasteDe(leer, par)).toBeGreaterThanOrEqual(UMBRALES[par.tipo]);
    },
  );

  it('los tonos vivos solo definen roles decorativos y el indicador del ítem activo', () => {
    const usos = [...TOKENS.matchAll(/(--q-[\w-]+)\s*:([^;]*)/g)]
      .filter(([, , valor]) => /--q-(naranja|cian)-500\b/.test(valor ?? ''))
      .map(([, nombre]) => nombre ?? '');
    expect(usos.length).toBeGreaterThan(0);
    expect(usos.filter((n) => !n.startsWith('--q-deco-') && n !== '--q-nav-indicador')).toEqual([]);
  });

  it('ningún par de texto usa un rol decorativo como primer plano', () => {
    const texto = PARES.filter((p) => p.tipo !== 'no-textual');
    expect(texto.filter((p) => p.primerPlano.startsWith('--q-deco-'))).toEqual([]);
  });
});
