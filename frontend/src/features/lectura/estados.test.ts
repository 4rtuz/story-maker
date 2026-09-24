// CA-24 y VAL-15 en su parte unitaria: el estado de cada volumen sale del checkpoint y del índice.
import { describe, expect, it } from 'vitest';
import { estadosDeVolumen } from './estados';

describe('estados de volumen (CA-24)', () => {
  it('7 cerrados, el 8 en curso y del 9 al 24 pendientes', () => {
    const estados = estadosDeVolumen(24, { capitulo: 7 }, [1, 2, 3, 4, 5, 6, 7, 8]);
    expect(estados).toHaveLength(24);
    expect(estados.slice(0, 7).every((e) => e === 'cerrado')).toBe(true);
    expect(estados[7]).toBe('en_curso');
    expect(estados.slice(8).every((e) => e === 'pendiente')).toBe(true);
  });

  it('con checkpoint null ninguno está cerrado, y los del índice están en curso (VAL-15)', () => {
    const estados = estadosDeVolumen(5, null, [1, 2]);
    expect(estados).toEqual(['en_curso', 'en_curso', 'pendiente', 'pendiente', 'pendiente']);
  });
});
