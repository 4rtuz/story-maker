// CA-18, CA-19 y CA-55 en su parte unitaria, y VAL-11: la serie de tensión como función pura y
// su SVG con los colores de tokens.css leídos por el lector de tokens.
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { hex, lectorDeCss } from '../../shared/marca/lector-de-tokens';
import { filasDeTension, graficaDeTension, serieDeTension } from './tension';

const TOKENS = fs.readFileSync(path.join(import.meta.dirname, '../../shared/marca/tokens.css'), 'utf8');
const leer = lectorDeCss(TOKENS);

const escaleta = (curva: number[], actos: number[][]): Esquemas['Escaleta'] => ({
  schema_version: '1.0.0',
  actos: actos.map((capitulos, i) => ({ numero: i + 1, funcion_dramatica: `acto ${i + 1}`, capitulos })),
  puntos_de_giro: { detonante: 1, punto_medio: 3, crisis: 4, climax: 5, resolucion: 6 },
  curva_tension_objetivo: curva,
});

const CA18 = escaleta([2, 3, 4, 5, 6, 7], [[1, 2], [3, 4, 5, 6]]);

describe('serie (CA-18)', () => {
  const serie = serieDeTension([4, 5, null, 6, 7], CA18);

  it('dos tramos reales separados por el null, sin interpolar', () => {
    expect(serie.tramos).toEqual([
      [
        { capitulo: 1, valor: 4 },
        { capitulo: 2, valor: 5 },
      ],
      [
        { capitulo: 4, valor: 6 },
        { capitulo: 5, valor: 7 },
      ],
    ]);
    expect(serie.sinPuntuar).toEqual([3]);
  });

  it('dos bandas de acto y cinco giros', () => {
    expect(serie.bandas).toEqual([
      { acto: 1, desde: 1, hasta: 2 },
      { acto: 2, desde: 3, hasta: 6 },
    ]);
    expect(serie.giros.map((g) => g.capitulo)).toEqual([1, 3, 4, 5, 6]);
  });

  it('la tabla tiene 6 filas, «sin puntuar» en la 3 y «—» en la 6', () => {
    const filas = filasDeTension(serie);
    expect(filas).toHaveLength(6);
    expect(filas[2]).toEqual(['3', '4', 'sin puntuar']);
    expect(filas[5]).toEqual(['6', '7', '—']);
  });

  it('con más entradas reales que objetivo, el eje llega al mayor de los dos (D46)', () => {
    const larga = serieDeTension([1, 2, 3, 4, 5, 6, 7, 8], CA18);
    expect(larga.capitulos).toBe(8);
    expect(filasDeTension(larga)).toHaveLength(8);
    expect(filasDeTension(larga)[7]).toEqual(['8', '—', '8']);
  });

  it('todo null o vacío: sin tensión puntuada, con la curva objetivo', () => {
    for (const real of [[], [null, null]]) {
      const s = serieDeTension(real, CA18);
      expect(s.hayReal).toBe(false);
      expect(s.objetivo).toHaveLength(6);
    }
  });

  it('sin escaleta: solo la serie real, sin bandas ni giros (CA-19)', () => {
    const s = serieDeTension([4, 5], null);
    expect([s.objetivo, s.bandas, s.giros, s.hayEscaleta]).toEqual([[], [], [], false]);
    expect(s.tramos).toHaveLength(1);
  });
});

describe('SVG', () => {
  it('real continua en --q-primario y objetivo discontinua en --q-icono-cian (CA-55)', () => {
    const svg = graficaDeTension(serieDeTension([4, 5, null, 6, 7], CA18), leer);
    const reales = [...svg.querySelectorAll('.q-tension__real')];
    expect(reales).toHaveLength(2);
    expect(reales.every((p) => p.getAttribute('stroke') === hex(leer('--q-primario')))).toBe(true);
    const objetivo = svg.querySelector('.q-tension__objetivo');
    expect(objetivo?.getAttribute('stroke')).toBe(hex(leer('--q-icono-cian')));
    expect(objetivo?.getAttribute('stroke-dasharray')).toBeTruthy();
    expect(reales[0]?.getAttribute('stroke-dasharray')).toBeNull();
    expect(svg.querySelectorAll('.q-tension__banda')).toHaveLength(2);
    expect(svg.querySelectorAll('.q-tension__giro')).toHaveLength(5);
    expect(svg.querySelector('.q-tension__banda')?.getAttribute('fill')).toBe(hex(leer('--q-secundario-fondo')));
    expect(svg.querySelector('.q-tension__giro')?.getAttribute('stroke')).toBe(hex(leer('--q-texto-secundario')));
    expect(svg.textContent).toContain('Acto 1');
  });

  it('un cambio de --q-primario llega a la serie real sin tocar otro fichero (CA-55)', () => {
    const otro = lectorDeCss(TOKENS.replace('--q-primario: var(--q-naranja-700);', '--q-primario: var(--q-cian-700);'));
    const svg = graficaDeTension(serieDeTension([4, 5], CA18), otro);
    expect(svg.querySelector('.q-tension__real')?.getAttribute('stroke')).toBe(hex(leer('--q-cian-700')));
  });

  it('un valor real aislado entre nulls deja un elemento visible (VAL-11)', () => {
    const svg = graficaDeTension(serieDeTension([null, 5, null, 6], escaleta([2, 3, 4, 5], [[1, 2, 3, 4]])), leer);
    expect(svg.querySelectorAll('.q-tension__punto')).toHaveLength(2);
    expect(svg.querySelector('.q-tension__punto')?.getAttribute('r')).not.toBe('0');
  });
});
