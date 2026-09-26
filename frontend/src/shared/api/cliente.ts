// El cliente de la API: el único módulo del panel que sale a la red (RF-03; eslint lo hace cumplir).
// Una función por petición, tipada con esquema.gen.ts, con una señal que combina la de la vista con
// el plazo de 5 s. Los GET llevan solo la cabecera Accept; los únicos POST son los de /lanzamientos.
import type { components } from './esquema.gen';
import { deHttp, deRed, deTiempo, PLAZO_MS } from './errores';

/** Los tipos de las respuestas, tal como salen del OpenAPI (RF-02): `Esquemas['Config']`. */
export type Esquemas = components['schemas'];
type E = Esquemas;

/** `VITE_API_URL`, o la de uvicorn por defecto (RF-01, D15). */
export function urlBase(entorno: { VITE_API_URL?: string } = import.meta.env): string {
  return entorno.VITE_API_URL || 'http://127.0.0.1:8000';
}

const PLAZO = Symbol('plazo');

interface Respuesta {
  status: number;
  texto: string;
}

/** Estado y cuerpo, leídos dentro del plazo, o un ErrorDeApi. Si la vista aborta, rechaza con el
 * AbortError tal cual: no es un fallo de la API y nadie lo muestra. Los temporizadores son los de
 * la página, así que el reloj simulado de los tests los controla (VER-11). */
async function pedir(
  ruta: string,
  aceptar: string,
  senal?: AbortSignal,
  envio?: { cuerpo?: unknown },
): Promise<Respuesta> {
  const base = urlBase();
  const controlador = new AbortController();
  const plazo = setTimeout(() => controlador.abort(PLAZO), PLAZO_MS);
  const propagar = (): void => controlador.abort(senal?.reason);
  if (senal?.aborted) propagar();
  senal?.addEventListener('abort', propagar, { once: true });
  try {
    const conCuerpo = envio?.cuerpo !== undefined;
    const respuesta = await fetch(`${base}${ruta}`, {
      method: envio ? 'POST' : 'GET',
      headers: conCuerpo ? { Accept: aceptar, 'Content-Type': 'application/json' } : { Accept: aceptar },
      ...(conCuerpo ? { body: JSON.stringify(envio.cuerpo) } : {}),
      signal: controlador.signal,
    });
    return { status: respuesta.status, texto: await respuesta.text() };
  } catch (error) {
    if (controlador.signal.reason === PLAZO) throw deTiempo();
    if (senal?.aborted) throw error;
    throw deRed(base);
  } finally {
    clearTimeout(plazo);
    senal?.removeEventListener('abort', propagar);
  }
}

const correcta = ({ status }: Respuesta): boolean => status >= 200 && status < 300;

async function json<T>(ruta: string, senal?: AbortSignal): Promise<T> {
  const respuesta = await pedir(ruta, 'application/json', senal);
  if (!correcta(respuesta)) throw deHttp(respuesta.status, respuesta.texto);
  return JSON.parse(respuesta.texto) as T;
}

/** Como `json`, pero `status` es una respuesta correcta que vale null (D45). */
async function jsonONull<T>(ruta: string, status: number, senal?: AbortSignal): Promise<T | null> {
  const respuesta = await pedir(ruta, 'application/json', senal);
  if (respuesta.status === status) return null;
  if (!correcta(respuesta)) throw deHttp(respuesta.status, respuesta.texto);
  return JSON.parse(respuesta.texto) as T;
}

const novela = (slug: string): string => `/novelas/${encodeURIComponent(slug)}`;

export const novelas = (s?: AbortSignal) => json<E['CursorDeNovela'][]>('/novelas', s);
export const estado = (slug: string, s?: AbortSignal) => json<E['Estado']>(`${novela(slug)}/estado`, s);
export const capitulos = (slug: string, s?: AbortSignal) =>
  json<E['FrontmatterCapitulo'][]>(`${novela(slug)}/capitulos`, s);
export const manifiesto = (slug: string, runId: string, s?: AbortSignal) =>
  json<E['Manifest']>(`${novela(slug)}/runs/${encodeURIComponent(runId)}`, s);
export const config = (slug: string, s?: AbortSignal) => json<E['Config']>(`${novela(slug)}/config`, s);
export const checkpoint = (slug: string, s?: AbortSignal) =>
  json<E['Checkpoint'] | null>(`${novela(slug)}/checkpoint`, s);
/** Portada, índice y ficha de la lectura web (docs/lectura-web.md). */
export const libro = (slug: string, s?: AbortSignal) => json<E['Libro']>(`${novela(slug)}/libro`, s);
export const runs = (slug: string, s?: AbortSignal) => json<E['Manifest'][]>(`${novela(slug)}/runs`, s);

/** Las métricas de Langfuse que guardó `novela costes --guardar`, o null si no hay (spec 0015). */
export const metricas = (slug: string, s?: AbortSignal) =>
  jsonONull<E['InformeDeCostes']>(`${novela(slug)}/metricas`, 404, s);

/** La portada de `novela portada`, para un `<img>`: sin ella, la API responde 404 y la vista
 * pone la cubierta tipográfica (spec 0015). */
export const urlDePortada = (slug: string): string => `${urlBase()}${novela(slug)}/portada`;

/** El libro de regalo en PDF, para un enlace de descarga: la API lo construye con los capítulos
 * cerrados y lo sirve como adjunto (spec 0015, D8). */
export const urlDePdf = (slug: string): string => `${urlBase()}${novela(slug)}/pdf`;

/** null si la novela todavía no tiene escaleta: el 404 que RF-19 trata sin aviso. */
export const escaleta = (slug: string, s?: AbortSignal) =>
  jsonONull<E['Escaleta']>(`${novela(slug)}/escaleta`, 404, s);

/** null tras un 416: `desde` ya no está en el log y el encadenado vuelve a 0 (RF-22). */
export const log = (slug: string, runId: string, desde: number, s?: AbortSignal) =>
  jsonONull<E['TramoDeLog']>(`${novela(slug)}/runs/${encodeURIComponent(runId)}/log?desde=${desde}`, 416, s);

/** El markdown del capítulo, tal cual lo sirve la API. */
export async function capitulo(slug: string, n: number, senal?: AbortSignal): Promise<string> {
  const respuesta = await pedir(`${novela(slug)}/capitulos/${n}`, 'text/markdown', senal);
  if (!correcta(respuesta)) throw deHttp(respuesta.status, respuesta.texto);
  return respuesta.texto;
}

const lanzamientoDe = (slug: string): string => `/lanzamientos/${encodeURIComponent(slug)}`;

async function enviar(ruta: string, cuerpo?: unknown): Promise<E['Lanzamiento']> {
  const respuesta = await pedir(ruta, 'application/json', undefined, { cuerpo });
  if (!correcta(respuesta)) throw deHttp(respuesta.status, respuesta.texto);
  return JSON.parse(respuesta.texto) as E['Lanzamiento'];
}

/** Lanza `novela producir`: la novela de principio a fin, sin copiar ninguna orden. */
export const lanzar = (peticion: E['PeticionDeLanzamiento']) => enviar('/lanzamientos', peticion);
export const reanudar = (slug: string) => enviar(`${lanzamientoDe(slug)}/reanudar`);
export const detener = (slug: string) => enviar(`${lanzamientoDe(slug)}/detener`);
export const lanzamientos = (s?: AbortSignal) => json<E['Lanzamiento'][]>('/lanzamientos', s);
