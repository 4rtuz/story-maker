// El tablero de lanzamientos (spec 0015, RF-10; D6): una columna por fase y el paso de
// `novela producir` contado como lo contaría un editor. El registro de las sesiones no sale de aquí.
import type { Esquemas } from '../../shared/api/cliente';

type Fila = Esquemas['Lanzamiento'];

export const COLUMNAS: readonly { clave: string; titulo: string; estados: readonly Fila['estado'][] }[] = [
  { clave: 'proceso', titulo: 'En proceso', estados: ['en_marcha'] },
  { clave: 'pausa', titulo: 'En pausa', estados: ['detenido'] },
  { clave: 'bloqueada', titulo: 'Bloqueada', estados: ['fallido', 'interrumpido'] },
  { clave: 'terminada', titulo: 'Terminada', estados: ['terminado'] },
];

export function agrupar(filas: readonly Fila[]): { clave: string; titulo: string; filas: Fila[] }[] {
  return COLUMNAS.map(({ clave, titulo, estados }) => ({ clave, titulo, filas: filas.filter((f) => estados.includes(f.estado)) }));
}

/** El capítulo de un paso `capitulo NN`, o null si el paso es otro. */
const capitulo = (paso: string): number | null => {
  const m = /^capitulo (\d+)$/.exec(paso);
  return m ? Number(m[1]) : null;
};

const GERUNDIOS: Record<string, string> = {
  entorno: 'Preparando todo',
  nueva: 'Creando la biblia',
  auditoria: 'Haciendo la revisión final',
};
const ETAPAS: Record<string, string> = { entorno: 'la preparación', nueva: 'la biblia', auditoria: 'la revisión final' };

export function pasoLegible(f: Fila): string {
  const n = capitulo(f.paso);
  const etapa = n ? `el capítulo ${n}` : (ETAPAS[f.paso] ?? f.paso);
  const deEtapa = n ? `del capítulo ${n}` : `de ${etapa}`;
  switch (f.estado) {
    case 'terminado':
      return 'Lista para leer';
    case 'en_marcha': {
      const texto = n ? `Escribiendo el capítulo ${n}` : (GERUNDIOS[f.paso] ?? 'Trabajando');
      return f.detener_pedido ? `${texto} · se pausará al terminarlo` : texto;
    }
    case 'detenido':
      return `En pausa antes ${deEtapa}`;
    case 'fallido':
    case 'interrumpido':
      return `Se paró en ${etapa}`;
  }
}
