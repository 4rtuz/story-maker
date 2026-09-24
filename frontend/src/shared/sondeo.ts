// El sondeo de una vista (RF-05 a RF-07, D10, D45): cada recurso a su cadencia, nunca dos
// peticiones del mismo recurso a la vez, pausa con la pestaña oculta y ronda inmediata al volver,
// y todo cancelado al desmontar. Cada ronda informa si fue correcta; de eso salen, sin peticiones
// propias, la hora de la barra superior y el estado de la API de la barra lateral (D50).
import { ErrorDeApi } from './api/errores';

/** Los datos de la vista cada 10 s y el tramo del log cada 3 s (D10). */
export const CADA_DATOS = 10_000;
export const CADA_LOG = 3_000;

export interface Recurso {
  clave: string;
  /** Milisegundos entre rondas: 10 000 para los datos de la vista, 3 000 para el log. */
  cada: number;
  /** Pide y pinta. Rechaza con ErrorDeApi si la API falla; un AbortError no cuenta. */
  pedir(senal: AbortSignal): Promise<void>;
}

export interface Ronda {
  cada: number;
  correcta: boolean;
  errores: ErrorDeApi[];
  hora: Date;
}

export interface Sondeo {
  detener(): void;
}

export function sondear(recursos: Recurso[], alTerminar: (ronda: Ronda) => void): Sondeo {
  const vista = new AbortController();
  const enCurso = new Set<string>();
  const temporizadores = new Map<number, ReturnType<typeof setTimeout>>();
  const grupos = new Map<number, Recurso[]>();
  for (const r of recursos) grupos.set(r.cada, [...(grupos.get(r.cada) ?? []), r]);

  const oculta = (): boolean => document.visibilityState === 'hidden';

  async function ronda(cada: number): Promise<void> {
    clearTimeout(temporizadores.get(cada));
    if (vista.signal.aborted || oculta()) return;
    temporizadores.set(cada, setTimeout(() => void ronda(cada), cada));
    const lanzados = (grupos.get(cada) ?? []).filter((r) => !enCurso.has(r.clave));
    const resultados = await Promise.allSettled(
      lanzados.map(async (r) => {
        enCurso.add(r.clave);
        try {
          await r.pedir(vista.signal);
        } finally {
          enCurso.delete(r.clave);
        }
      }),
    );
    if (vista.signal.aborted) return;
    const errores = resultados.flatMap((r) =>
      r.status === 'rejected' && r.reason instanceof ErrorDeApi ? [r.reason] : [],
    );
    const abortada = resultados.some((r) => r.status === 'rejected' && !(r.reason instanceof ErrorDeApi));
    if (abortada && !errores.length) return;
    alTerminar({ cada, correcta: !errores.length && !abortada, errores, hora: new Date() });
  }

  const rondas = (): void => {
    for (const cada of grupos.keys()) void ronda(cada);
  };
  // Oculta, la ronda que toque se salta sin reprogramarse; al volver, ronda inmediata (RF-06).
  const alCambiarVisibilidad = (): void => {
    if (!oculta()) rondas();
  };
  document.addEventListener('visibilitychange', alCambiarVisibilidad);
  rondas();

  return {
    detener() {
      vista.abort();
      for (const t of temporizadores.values()) clearTimeout(t);
      document.removeEventListener('visibilitychange', alCambiarVisibilidad);
    },
  };
}
