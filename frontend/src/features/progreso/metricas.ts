// Las métricas de Langfuse de Progreso (spec 0015, §5.2): el informe que guarda `novela costes
// --guardar`, resumido para pintarlo. Puro.
import type { Esquemas } from '../../shared/api/cliente';

type Informe = Esquemas['InformeDeCostes'];

export interface PuntoDeCapitulo {
  n: number;
  coste: number;
  segundos: number;
  llamadas: number;
}

export interface CosteDeRol {
  rol: string;
  nombre: string;
  coste: number;
  fraccion: number;
}

export interface ResumenDeCostes {
  coste: string;
  tiempo: string;
  llamadas: string;
  tokens: string;
  cache: string;
  medioPorCapitulo: string;
  capitulos: PuntoDeCapitulo[];
  roles: CosteDeRol[];
}

export const usd = (n: number): string => n.toLocaleString('es-ES', { style: 'currency', currency: 'USD' });
const compacto = (n: number): string => n.toLocaleString('es-ES', { notation: 'compact', maximumFractionDigits: 1 });

export function duracion(segundos: number): string {
  if (segundos < 60) return `${Math.round(segundos)} s`;
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `${minutos} min`;
  const [h, m] = [Math.floor(minutos / 60), minutos % 60];
  return m ? `${h} h ${m} min` : `${h} h`;
}

const NOMBRES: Record<string, string> = { 'editor-estilo': 'Editor de estilo', 'lector-suspense': 'Lector de suspense' };
const nombreDe = (rol: string): string => NOMBRES[rol] ?? `${rol[0]?.toUpperCase() ?? ''}${rol.slice(1).replaceAll('-', ' ')}`;

export function resumirCostes(informe: Informe): ResumenDeCostes {
  const { total } = informe;
  const capitulos = informe.pasos.flatMap((p) => {
    const m = /^capitulo (\d+)$/.exec(p.paso);
    return m ? [{ n: Number(m[1]), coste: p.coste_usd, segundos: p.latencia_s, llamadas: p.llamadas }] : [];
  });
  const porRol = new Map<string, number>();
  for (const p of informe.pasos) for (const [rol, c] of Object.entries(p.roles)) porRol.set(rol, (porRol.get(rol) ?? 0) + c.coste_usd);
  const suma = [...porRol.values()].reduce((a, b) => a + b, 0) || 1;
  const roles = [...porRol]
    .map(([rol, coste]) => ({ rol, nombre: nombreDe(rol), coste, fraccion: coste / suma }))
    .sort((a, b) => b.coste - a.coste || a.nombre.localeCompare(b.nombre, 'es'));
  const costeCapitulos = capitulos.reduce((a, c) => a + c.coste, 0);
  return {
    coste: usd(total.coste_usd),
    tiempo: duracion(total.latencia_s),
    llamadas: total.llamadas.toLocaleString('es-ES'),
    tokens: compacto(total.tokens_entrada + total.tokens_salida),
    cache: `${Math.round((100 * total.tokens_cache_lectura) / (total.tokens_entrada || 1))} %`,
    medioPorCapitulo: usd(capitulos.length ? costeCapitulos / capitulos.length : 0),
    capitulos,
    roles,
  };
}
