// «Proceso de creación» (spec 0015, RF-11): los hitos de la novela y el porcentaje de la barra, a
// partir de la escaleta, el checkpoint, el cursor y el lanzamiento. Puro. Un hito conserva su
// clave al pasar de «en curso» a «hecho», para que la vista anime solo ese cambio.
import type { Esquemas } from '../../shared/api/cliente';

type E = Esquemas;

export interface EntradaDeProceso {
  total: number;
  hayEscaleta: boolean;
  cerrados: number;
  cursor: E['Cursor'] | null;
  lanzamiento: E['Lanzamiento'] | null;
}

export interface Hito {
  clave: string;
  texto: string;
  estado: 'hecho' | 'en-curso' | 'parado';
}

export interface Proceso {
  porcentaje: number;
  hitos: Hito[];
}

/** Escrito, evaluado y aceptado: en qué subpaso va el capítulo según la fase del cursor. */
const SUBPASOS = ['escrito', 'evaluado', 'aceptado'] as const;
const GERUNDIOS = ['Escribiendo', 'Evaluando', 'Aceptando'] as const;
const SUBPASO_DE_FASE: Record<E['Cursor']['fase'], number> = { escritura: 0, revision: 1, registro: 2, cerrado: 2 };

export function proceso({ total, hayEscaleta, cerrados, cursor, lanzamiento }: EntradaDeProceso): Proceso {
  const enMarcha = lanzamiento?.estado === 'en_marcha';
  const parada = !lanzamiento ? 'pendiente' : lanzamiento.estado === 'detenido' ? 'en pausa' : 'bloqueado';
  /** El hito que toca ahora: gira si hay proceso en marcha; si no, dice por qué está quieto. */
  const actual = (clave: string, gerundio: string, sujeto: string, femenino = false): Hito =>
    enMarcha
      ? { clave, texto: gerundio, estado: 'en-curso' }
      : { clave, texto: `${sujeto} ${femenino ? parada.replace(/o$/, 'a') : parada}`, estado: 'parado' };

  const unidades = 2 + 3 * total;
  const porcentaje = (hechas: number): number => Math.round((100 * hechas) / unidades);

  if (!hayEscaleta) return { porcentaje: 0, hitos: [actual('biblia', 'Creando la biblia', 'Biblia', true)] };
  const hitos: Hito[] = [{ clave: 'biblia', texto: 'Biblia creada', estado: 'hecho' }];
  for (let c = 1; c <= cerrados; c++) hitos.push({ clave: `cap-${c}-aceptado`, texto: `Capítulo ${c} aceptado`, estado: 'hecho' });

  if (cerrados >= total) {
    const terminada = !lanzamiento || lanzamiento.estado === 'terminado';
    hitos.push(
      terminada
        ? { clave: 'final', texto: 'Novela terminada', estado: 'hecho' }
        : actual('final', 'Haciendo la revisión final', 'Revisión final', true),
    );
    return { porcentaje: porcentaje(unidades - (terminada ? 0 : 1)), hitos };
  }

  const c = cerrados + 1;
  const subpaso = cursor?.capitulo === c ? SUBPASO_DE_FASE[cursor.fase] : 0;
  for (const s of SUBPASOS.slice(0, subpaso)) hitos.push({ clave: `cap-${c}-${s}`, texto: `Capítulo ${c} ${s}`, estado: 'hecho' });
  hitos.push(actual(`cap-${c}-${SUBPASOS[subpaso]}`, `${GERUNDIOS[subpaso]} el capítulo ${c}`, `Capítulo ${c}`));
  return { porcentaje: porcentaje(1 + 3 * cerrados + subpaso), hitos };
}
