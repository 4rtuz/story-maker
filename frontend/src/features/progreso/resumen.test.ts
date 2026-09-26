// CA-17 con el formato de la spec 0015: las cifras de Progreso, para leer. Los cerrados salen del
// checkpoint, no del cursor.
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { resumir } from './resumen';

const estado = {
  cursor: { capitulo: 8, fase: 'escritura', ultimo_paso: 'briefing', intento: 2 },
  metricas: { palabras_totales: 11397, desviacion_vs_plan: -0.125 },
} as unknown as Esquemas['Estado'];

const config = {
  parametros_obra: { num_capitulos: 24, longitud_total_palabras: 72000 },
} as unknown as Esquemas['Config'];

describe('resumir (CA-17)', () => {
  it('con 7 cerrados de 24', () => {
    const r = resumir(estado, config, { capitulo: 7 } as Esquemas['Checkpoint']);
    expect([r.numeroCerrados, r.cerrados]).toEqual(['7', 'de 24 capítulos']);
  });

  it('con checkpoint null, ninguno', () => {
    expect(resumir(estado, config, null).numeroCerrados).toBe('0');
  });

  it('palabras junto a las previstas, con separador de miles', () => {
    const r = resumir(estado, config, null);
    expect([r.palabras, r.palabrasObjetivo]).toEqual(['11.397', 'de 72.000 previstas']);
  });
});
