// La actividad del bucle (RF-22, RF-23; D2, D38, D48): las últimas líneas de harness.log del run
// de run_id mayor, pedidas cada 3 s con el hasta de la respuesta anterior. No hay selección de
// run: al aparecer uno mayor se sigue ese, desde 0. El encadenado es una función pura; la
// tarjeta, su cáscara.
import * as api from '../../shared/api/cliente';
import { CADA_LOG, type Recurso } from '../../shared/sondeo';
import { el, esqueleto, estadoVacio, etiqueta, tarjeta, vacio } from '../../shared/ui/componentes';

export const LINEAS_VISIBLES = 50;
const QUINCE_MINUTOS = 15 * 60_000;

export interface Registro {
  runId: string | null;
  desde: number;
  lineas: string[];
  modificado: string | null;
}

export const REGISTRO_VACIO: Registro = { runId: null, desde: 0, lineas: [], modificado: null };

/** El run a seguir es el de run_id mayor; si cambia, se empieza de nuevo desde 0. */
export function seguir(registro: Registro, runs: api.Esquemas['Manifest'][]): Registro {
  const mayor = runs.map((r) => r.run_id).sort().at(-1) ?? null;
  return mayor === registro.runId ? registro : { ...REGISTRO_VACIO, runId: mayor };
}

/** Un tramo nuevo se añade; null, el 416 de un desde que ya no está en el log, reinicia. */
export function aplicarTramo(registro: Registro, tramo: api.Esquemas['TramoDeLog'] | null): Registro {
  if (tramo === null) return { ...REGISTRO_VACIO, runId: registro.runId };
  return {
    runId: registro.runId,
    desde: tramo.hasta,
    lineas: [...registro.lineas, ...tramo.lineas].slice(-LINEAS_VISIBLES),
    modificado: tramo.modificado,
  };
}

/** Más de 15 min desde la última escritura, comparando instantes con zona; una escritura en el
 * futuro, por un reloj desajustado, no cuenta (VAL-14). */
export function sinActividad(modificado: string | null, ahora: Date): boolean {
  if (modificado === null) return false;
  return ahora.getTime() - Date.parse(modificado) > QUINCE_MINUTOS;
}

const hora = (iso: string): string => new Date(iso).toTimeString().slice(0, 8);

export function crearActividad(slug: string) {
  let registro = REGISTRO_VACIO;
  let conRuns = false;
  const t = tarjeta({ titulo: 'Actividad', icono: 'terminal', tono: 'cian', clase: 'q-actividad' });
  t.cuerpo.append(esqueleto('q-esqueleto--lista'));

  function pintar(): void {
    if (!conRuns || !registro.runId) {
      t.cuerpo.replaceChildren(
        estadoVacio({ icono: 'terminal', texto: 'sin runs todavía', pista: 'La actividad aparece con el primer paso del bucle.' }),
      );
      return;
    }
    const meta = el('p', 'q-actividad__meta', el('span', 'q-run__id', registro.runId));
    if (registro.modificado === null) {
      meta.append(etiqueta('sin actividad registrada'));
    } else {
      const escrito = el('time', 'q-fecha', `última escritura ${hora(registro.modificado)}`);
      escrito.dateTime = registro.modificado;
      meta.append(escrito);
      if (sinActividad(registro.modificado, new Date())) meta.append(etiqueta(`sin actividad desde ${hora(registro.modificado)}`));
    }
    const log = el('ol', 'q-log', ...registro.lineas.map((l) => el('li', 'q-log__linea', l)));
    log.tabIndex = 0; // se desplaza con teclado
    log.setAttribute('aria-label', `Últimas líneas de harness.log de ${registro.runId}`);
    t.cuerpo.replaceChildren(meta, registro.lineas.length ? log : vacio('todavía no hay líneas en el log'));
    log.scrollTop = log.scrollHeight;
  }

  const recurso: Recurso = {
    clave: 'log',
    cada: CADA_LOG,
    async pedir(senal) {
      const { runId, desde } = registro;
      if (!runId) return; // sin runs, ninguna petición de log
      const tramo = await api.log(slug, runId, desde, senal);
      if (registro.runId !== runId) return; // llegó un run mayor mientras tanto
      registro = aplicarTramo(registro, tramo);
      pintar();
    },
  };

  return {
    tarjeta: t.raiz,
    recurso,
    alCambiarRuns(runs: api.Esquemas['Manifest'][]): void {
      conRuns = runs.length > 0;
      const antes = registro.runId;
      registro = seguir(registro, runs);
      if (registro.runId !== antes || !conRuns) pintar();
    },
  };
}
