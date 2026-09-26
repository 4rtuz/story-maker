// Lo que el panel dice de una novela en una línea (spec 0015): su subgénero con rótulo y su estado
// en una palabra, con el tono del punto que lo acompaña.
import type { Esquemas } from './api/cliente';

type Subgenero = Esquemas['ParametrosObra']['subgenero'];

// Exhaustiva sobre el tipo generado: un subgénero nuevo en el backend rompe tsc aquí (VER-17).
export const SUBGENEROS = {
  thriller_psicologico: 'Thriller psicológico',
  noir: 'Noir',
  domestic_suspense: 'Suspense doméstico',
  procedural: 'Procedimental',
} as const satisfies Record<Subgenero, string>;

export type TonoDeEstado = 'hecho' | 'vivo' | 'pausa' | 'bloqueo' | 'neutro';

export function estadoDeObra(
  cerrados: number,
  total: number,
  lanzamiento: Esquemas['Lanzamiento'] | null | undefined,
): { texto: string; tono: TonoDeEstado } {
  if (lanzamiento?.estado === 'en_marcha') return { texto: 'Escribiéndose', tono: 'vivo' };
  if (total > 0 && cerrados >= total) return { texto: 'Terminada', tono: 'hecho' };
  if (lanzamiento?.estado === 'detenido') return { texto: 'En pausa', tono: 'pausa' };
  if (lanzamiento?.estado === 'fallido' || lanzamiento?.estado === 'interrumpido') return { texto: 'Bloqueada', tono: 'bloqueo' };
  return { texto: 'Sin terminar', tono: 'neutro' };
}
