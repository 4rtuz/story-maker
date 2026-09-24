// CA-17 y CA-20: el resumen de Progreso, tal como lo sirve la API.
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { hilosAbiertos, resumir } from './resumen';

const hilo = (id: string, estado: 'abierto' | 'cerrado', abierto_en: number): Esquemas['Hilo'] => ({
  id,
  estado,
  abierto_en,
  cerrado_en: estado === 'cerrado' ? 3 : null,
  descripcion: `descripción de ${id}`,
});

const estado = {
  cursor: { capitulo: 8, fase: 'escritura', ultimo_paso: 'briefing', intento: 2 },
  metricas: { palabras_totales: 2100, desviacion_vs_plan: -0.125 },
  hilos: [hilo('hil-001', 'abierto', 1), hilo('hil-002', 'cerrado', 2)],
} as unknown as Esquemas['Estado'];

const config = {
  parametros_obra: { num_capitulos: 24, longitud_total_palabras: 7200 },
} as unknown as Esquemas['Config'];

describe('resumir (CA-17)', () => {
  it('con 7 cerrados de 24, «cerrados: 7 de 24»', () => {
    const r = resumir(estado, config, { capitulo: 7 } as Esquemas['Checkpoint']);
    expect(r.cerrados).toBe('cerrados: 7 de 24');
    expect(r.numeroCerrados).toBe('7');
  });

  it('con checkpoint null, «cerrados: 0 de 24»', () => {
    expect(resumir(estado, config, null).cerrados).toBe('cerrados: 0 de 24');
  });

  it('palabras junto al total y desviación, tal cual', () => {
    const r = resumir(estado, config, null);
    expect([r.palabras, r.palabrasObjetivo, r.desviacion]).toEqual(['2100', 'de 7200', '-0.125']);
  });

  it('el cursor, tal cual', () => {
    expect(resumir(estado, config, null).cursor).toEqual(estado.cursor);
  });
});

describe('hilos abiertos (CA-20)', () => {
  it('solo los de estado abierto', () => {
    expect(hilosAbiertos(estado).map((h) => [h.id, h.abierto_en, h.descripcion])).toEqual([
      ['hil-001', 1, 'descripción de hil-001'],
    ]);
  });
});
