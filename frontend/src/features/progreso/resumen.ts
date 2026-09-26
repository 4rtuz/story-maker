// Las cifras de Progreso (RF-17, spec 0015): capítulos y palabras, para leer. Los cerrados salen
// del checkpoint, no del cursor, como en novela estado --breve.
import type { Esquemas } from '../../shared/api/cliente';

export interface Resumen {
  numeroCerrados: string;
  cerrados: string;
  palabras: string;
  palabrasObjetivo: string;
}

const miles = (n: number): string => n.toLocaleString('es-ES', { useGrouping: 'always' } as Intl.NumberFormatOptions);

export function resumir(estado: Esquemas['Estado'], config: Esquemas['Config'], checkpoint: Esquemas['Checkpoint'] | null): Resumen {
  const obra = config.parametros_obra;
  return {
    numeroCerrados: String(checkpoint?.capitulo ?? 0),
    cerrados: `de ${obra.num_capitulos} capítulos`,
    palabras: miles(estado.metricas.palabras_totales),
    palabrasObjetivo: `de ${miles(obra.longitud_total_palabras)} previstas`,
  };
}
