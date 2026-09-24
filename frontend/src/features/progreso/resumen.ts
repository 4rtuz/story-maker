// El resumen de Progreso (RF-17, RF-20; D4, D8): los valores tal como los sirve la API. Los
// cerrados salen del checkpoint, no del cursor, como en novela estado --breve.
import type { Esquemas } from '../../shared/api/cliente';

export interface Resumen {
  cursor: Esquemas['Cursor'];
  numeroCerrados: string;
  cerrados: string;
  palabras: string;
  palabrasObjetivo: string;
  desviacion: string;
}

export function resumir(
  estado: Esquemas['Estado'],
  config: Esquemas['Config'],
  checkpoint: Esquemas['Checkpoint'] | null,
): Resumen {
  const cerrados = checkpoint?.capitulo ?? 0;
  const obra = config.parametros_obra;
  return {
    cursor: estado.cursor,
    numeroCerrados: String(cerrados),
    cerrados: `cerrados: ${cerrados} de ${obra.num_capitulos}`,
    palabras: String(estado.metricas.palabras_totales),
    palabrasObjetivo: `de ${obra.longitud_total_palabras}`,
    desviacion: String(estado.metricas.desviacion_vs_plan),
  };
}

export function hilosAbiertos(estado: Esquemas['Estado']): Esquemas['Hilo'][] {
  return estado.hilos.filter((h) => h.estado === 'abierto');
}
