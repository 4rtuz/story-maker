// «Proceso de creación» (spec 0015, RF-11): hitos y porcentaje a partir de lo que ya sirve la API.
// Cada capítulo pesa tres unidades (escrito, evaluado, aceptado); la biblia y el cierre, una.
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { proceso, type EntradaDeProceso } from './proceso';

type E = Esquemas;
const cursor = (capitulo: number, fase: E['Cursor']['fase']): E['Cursor'] => ({ capitulo, fase, ultimo_paso: null, intento: 1 });
const lanz = (estado: E['Lanzamiento']['estado'], paso = 'capitulo 03'): E['Lanzamiento'] => ({
  slug: 'demo',
  estado,
  paso,
  detalle: '',
  actualizado: '2026-09-25T10:00:00Z',
  detener_pedido: false,
  registro: [],
});
const base: EntradaDeProceso = { total: 10, hayEscaleta: true, cerrados: 0, cursor: null, lanzamiento: lanz('en_marcha') };
const textos = (e: EntradaDeProceso) => proceso(e).hitos.map((h) => `${h.estado}: ${h.texto}`);

describe('proceso de creación', () => {
  it('sin escaleta y en marcha, creando la biblia', () => {
    const p = proceso({ ...base, hayEscaleta: false, lanzamiento: lanz('en_marcha', 'nueva') });
    expect(p.hitos).toEqual([{ clave: 'biblia', texto: 'Creando la biblia', estado: 'en-curso' }]);
    expect(p.porcentaje).toBe(0);
  });

  it('biblia hecha y primer capítulo en escritura', () => {
    const p = proceso({ ...base, cursor: cursor(1, 'escritura') });
    expect(textos({ ...base, cursor: cursor(1, 'escritura') })).toEqual(['hecho: Biblia creada', 'en-curso: Escribiendo el capítulo 1']);
    expect(p.porcentaje).toBe(3);
  });

  it('en revisión: el capítulo ya está escrito y se evalúa', () => {
    const e = { ...base, cerrados: 2, cursor: cursor(3, 'revision') };
    expect(textos(e)).toEqual([
      'hecho: Biblia creada',
      'hecho: Capítulo 1 aceptado',
      'hecho: Capítulo 2 aceptado',
      'hecho: Capítulo 3 escrito',
      'en-curso: Evaluando el capítulo 3',
    ]);
    expect(proceso(e).porcentaje).toBe(25);
  });

  it('en registro: evaluado y aceptándose', () => {
    expect(textos({ ...base, cerrados: 2, cursor: cursor(3, 'registro') }).slice(-2)).toEqual([
      'hecho: Capítulo 3 evaluado',
      'en-curso: Aceptando el capítulo 3',
    ]);
  });

  it('el mismo hito conserva su clave al pasar de en curso a hecho', () => {
    const antes = proceso({ ...base, cerrados: 2, cursor: cursor(3, 'escritura') }).hitos.at(-1);
    const despues = proceso({ ...base, cerrados: 2, cursor: cursor(3, 'revision') }).hitos.find((h) => h.clave === antes?.clave);
    expect(despues?.estado).toBe('hecho');
  });

  it('un cursor que se quedó en el capítulo cerrado apunta al siguiente', () => {
    expect(textos({ ...base, cerrados: 2, cursor: cursor(2, 'registro') }).at(-1)).toBe('en-curso: Escribiendo el capítulo 3');
  });

  it.each<[E['Lanzamiento'] | null, string]>([
    [lanz('detenido'), 'parado: Capítulo 3 en pausa'],
    [lanz('fallido'), 'parado: Capítulo 3 bloqueado'],
    [lanz('interrumpido'), 'parado: Capítulo 3 bloqueado'],
    [null, 'parado: Capítulo 3 pendiente'],
  ])('sin proceso en marcha (%o), el hito actual no gira', (lanzamiento, texto) => {
    expect(textos({ ...base, cerrados: 2, cursor: cursor(3, 'escritura'), lanzamiento }).at(-1)).toBe(texto);
  });

  it('todo cerrado y sin lanzamiento: terminada, al 100 %', () => {
    const e = { ...base, cerrados: 10, cursor: cursor(10, 'registro'), lanzamiento: null };
    expect(textos(e).at(-1)).toBe('hecho: Novela terminada');
    expect(proceso(e).porcentaje).toBe(100);
  });

  it('todo cerrado y auditando: la revisión final en curso', () => {
    const e = { ...base, cerrados: 10, cursor: cursor(10, 'registro'), lanzamiento: lanz('en_marcha', 'auditoria') };
    expect(textos(e).at(-1)).toBe('en-curso: Haciendo la revisión final');
    expect(proceso(e).porcentaje).toBe(97);
  });
});
