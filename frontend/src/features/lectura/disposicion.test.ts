// CA-24 y VAL-12 en su parte unitaria: x = (n − 1) × 1,2 + a × 2,0, con a los actos anteriores.
import { describe, expect, it } from 'vitest';
import { disposicion } from './disposicion';

const acto = (numero: number, capitulos: number[]) => ({ numero, funcion_dramatica: '', capitulos });
const TRES_ACTOS = [acto(1, [1, 2, 3, 4, 5, 6]), acto(2, [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]), acto(3, [19, 20, 21, 22, 23, 24])];
const cerca = (a: number, b: number) => Math.abs(a - b) < 1e-9;

describe('disposición (CA-24)', () => {
  it('x estrictamente creciente, y el hueco entre actos mayor que dentro de un acto', () => {
    const x = disposicion(24, TRES_ACTOS);
    expect(x).toHaveLength(24);
    for (let i = 1; i < x.length; i++) expect(x[i]!).toBeGreaterThan(x[i - 1]!);
    const paso = x[1]! - x[0]!;
    expect(x[6]! - x[5]!).toBeGreaterThan(paso);
    expect(x[18]! - x[17]!).toBeGreaterThan(paso);
    expect(cerca(x[6]!, 6 * 1.2 + 2)).toBe(true);
    expect(cerca(x[23]!, 23 * 1.2 + 4)).toBe(true);
  });

  it('sin escaleta, paso constante de 1,2 (VAL-12)', () => {
    const x = disposicion(999, null);
    for (let i = 1; i < x.length; i++) expect(cerca(x[i]! - x[i - 1]!, 1.2)).toBe(true);
  });

  it('un capítulo fuera de acto se coloca por su número, sin hueco propio', () => {
    // El 4 no figura en ningún acto: lleva los actos anteriores a su número, y ninguno más.
    const x = disposicion(6, [acto(1, [1, 2, 3]), acto(2, [5, 6])]);
    expect(cerca(x[3]!, 3 * 1.2 + 1 * 2)).toBe(true);
    expect(cerca(x[4]! - x[3]!, 1.2)).toBe(true);
    for (let i = 1; i < x.length; i++) expect(x[i]!).toBeGreaterThan(x[i - 1]!);
  });
});
