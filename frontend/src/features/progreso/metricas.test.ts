// Las métricas de Langfuse de Progreso (spec 0015, §5.2): del informe de `novela costes --guardar`
// a lo que se pinta, por novela, por capítulo y por rol.
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { duracion, resumirCostes, usd } from './metricas';

type Informe = Esquemas['InformeDeCostes'];
const consumo = (coste: number, extra: object = {}) => ({
  llamadas: 10,
  tokens_entrada: 1000,
  tokens_salida: 100,
  tokens_cache_lectura: 800,
  coste_usd: coste,
  latencia_media_llamada_s: 2,
  ...extra,
});
const informe: Informe = {
  slug: 'demo',
  sesion: 'novela-demo',
  generado: '2026-09-25T10:00:00Z',
  pasos: [
    { paso: 'nueva', ...consumo(1), latencia_s: 600, roles: { arquitecto: consumo(1) } },
    { paso: 'capitulo 01', ...consumo(2), latencia_s: 900, roles: { escritor: consumo(1.5), orquestador: consumo(0.5) } },
    { paso: 'capitulo 02', ...consumo(3), latencia_s: 1200, roles: { escritor: consumo(2), 'lector-suspense': consumo(1) } },
  ],
  total: { ...consumo(6, { llamadas: 30, tokens_entrada: 3000, tokens_salida: 300, tokens_cache_lectura: 2400 }), latencia_s: 2700 },
};

describe('resumirCostes', () => {
  it('totales de la novela con formato de lectura', () => {
    const r = resumirCostes(informe);
    expect(r.coste).toBe(usd(6));
    expect(r.tiempo).toBe('45 min');
    expect(r.llamadas).toBe('30');
    expect(r.cache).toBe('80 %');
  });

  it('un punto por capítulo, sin la biblia ni la auditoría', () => {
    expect(resumirCostes(informe).capitulos).toEqual([
      { n: 1, coste: 2, segundos: 900, llamadas: 10 },
      { n: 2, coste: 3, segundos: 1200, llamadas: 10 },
    ]);
    expect(resumirCostes(informe).medioPorCapitulo).toBe(usd(2.5));
  });

  it('el coste por rol, sumado en toda la novela y de mayor a menor', () => {
    expect(resumirCostes(informe).roles.map((r) => [r.nombre, r.coste])).toEqual([
      ['Escritor', 3.5],
      ['Arquitecto', 1],
      ['Lector de suspense', 1],
      ['Orquestador', 0.5],
    ]);
    expect(resumirCostes(informe).roles[0]?.fraccion).toBeCloseTo(3.5 / 6);
  });
});

describe('duracion', () => {
  it.each([
    [42, '42 s'],
    [600, '10 min'],
    [3600, '1 h'],
    [8040, '2 h 14 min'],
  ])('%d s es «%s»', (s, texto) => {
    expect(duracion(s)).toBe(texto);
  });
});
