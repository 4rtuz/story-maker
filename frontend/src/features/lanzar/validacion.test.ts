// CA-12 y CA-13: cada campo inválido da su motivo sin normalizar nada (D41, D42), y el slug se
// comprueba contra GET /novelas, o se avisa de que no se ha podido (D43).
import { describe, expect, it } from 'vitest';
import { comprobarSlug, validar, type Campos } from './validacion';

const base: Campos = { slug: 'nueva-prueba', idea: 'Un faro apagado.', capitulos: '', palabras: '' };

const INVALIDOS: [Partial<Campos>, keyof Campos][] = [
  [{ slug: 'Nueva_Prueba' }, 'slug'],
  [{ slug: '' }, 'slug'],
  [{ idea: '   ' }, 'idea'],
  [{ idea: '\t\n' }, 'idea'],
  [{ idea: '' }, 'idea'],
  ...['0', '1000', '2.5', '07', ' 3', '+3', '3 ', '-1', 'tres'].map(
    (c): [Partial<Campos>, keyof Campos] => [{ capitulos: c }, 'capitulos'],
  ),
  ...['0', '09000', '-1', '9 000', '1e4'].map((p): [Partial<Campos>, keyof Campos] => [{ palabras: p }, 'palabras']),
];

describe('validar (CA-12)', () => {
  it.each(INVALIDOS)('%o da su motivo en %s', (cambio, campo) => {
    const errores = validar({ ...base, ...cambio });
    expect(Object.keys(errores)).toEqual([campo]);
    expect(errores[campo]).toBeTruthy();
  });

  it.each([
    [{ capitulos: '1', palabras: '1' }],
    [{ capitulos: '999' }],
    [{ capitulos: '', palabras: '80000' }],
    [{ idea: '  Una idea con espacios alrededor  ' }],
  ])('%o es válido y no se normaliza', (cambio) => {
    expect(validar({ ...base, ...cambio })).toEqual({});
  });
});

describe('comprobarSlug (CA-13)', () => {
  it('un slug existente da el texto de CA-13', () => {
    expect(comprobarSlug('demo-24', ['demo-24', 'recien-creada'])).toEqual({
      error: 'ya existe una novela demo-24: novela nueva saldrá con 1 sin tocar nada',
    });
  });

  it('uno libre, nada', () => {
    expect(comprobarSlug('nueva-prueba', ['demo-24'])).toEqual({});
  });

  it('sin la lista, la orden sale con el aviso de D43', () => {
    expect(comprobarSlug('demo-24', null)).toEqual({ aviso: 'no se ha podido comprobar si el slug ya existe' });
  });
});
