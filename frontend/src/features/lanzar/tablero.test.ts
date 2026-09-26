// El tablero de lanzamientos (spec 0015, RF-10; D6): cuatro columnas por estado y el paso en
// lenguaje de lector, sin nombres de sesión ni de agente.
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { agrupar, COLUMNAS, pasoLegible } from './tablero';

type Fila = Esquemas['Lanzamiento'];
const fila = (slug: string, estado: Fila['estado'], paso = 'capitulo 04', extra: Partial<Fila> = {}): Fila => ({
  slug,
  estado,
  paso,
  detalle: 'escritura, revisión y registro',
  actualizado: '2026-09-25T10:00:00Z',
  detener_pedido: false,
  registro: ['[10:00] /novela-continuar'],
  ...extra,
});

describe('tablero', () => {
  it('cuatro columnas en orden, cada estado en una sola', () => {
    expect(COLUMNAS.map((c) => c.titulo)).toEqual(['En proceso', 'En pausa', 'Bloqueada', 'Terminada']);
    const estados = COLUMNAS.flatMap((c) => c.estados).sort();
    expect(estados).toEqual(['detenido', 'en_marcha', 'fallido', 'interrumpido', 'terminado']);
  });

  it('reparte los lanzamientos por su estado', () => {
    const grupos = agrupar([fila('a', 'en_marcha'), fila('b', 'fallido'), fila('c', 'interrumpido'), fila('d', 'detenido'), fila('e', 'terminado')]);
    expect(grupos.map((g) => g.filas.map((f) => f.slug))).toEqual([['a'], ['d'], ['b', 'c'], ['e']]);
  });

  it.each<[Fila, string]>([
    [fila('a', 'en_marcha', 'entorno'), 'Preparando todo'],
    [fila('a', 'en_marcha', 'nueva'), 'Creando la biblia'],
    [fila('a', 'en_marcha', 'capitulo 04'), 'Escribiendo el capítulo 4'],
    [fila('a', 'en_marcha', 'auditoria'), 'Haciendo la revisión final'],
    [fila('a', 'en_marcha', 'capitulo 04', { detener_pedido: true }), 'Escribiendo el capítulo 4 · se pausará al terminarlo'],
    [fila('a', 'detenido', 'capitulo 07'), 'En pausa antes del capítulo 7'],
    [fila('a', 'fallido', 'capitulo 07'), 'Se paró en el capítulo 7'],
    [fila('a', 'interrumpido', 'nueva'), 'Se paró en la biblia'],
    [fila('a', 'terminado', 'auditoria'), 'Lista para leer'],
  ])('%o se lee «%s»', (f, texto) => {
    expect(pasoLegible(f)).toBe(texto);
  });
});
