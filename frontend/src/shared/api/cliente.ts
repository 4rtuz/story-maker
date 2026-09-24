// El cliente de la API: el único módulo del panel que sale a la red (RF-03; eslint lo hace cumplir).
// Una función por GET, tipada con esquema.gen.ts, con method GET, solo la cabecera Accept y una
// señal que combina la de la vista con el plazo de 5 s.
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
async function pedir(ruta: string, aceptar: string, senal?: AbortSignal): Promise<Respuesta> {
  const base = urlBase();
  const controlador = new AbortController();
  const plazo = setTimeout(() => controlador.abort(PLAZO), PLAZO_MS);
  const propagar = (): void => controlador.abort(senal?.reason);
  if (senal?.aborted) propagar();
  senal?.addEventListener('abort', propagar, { once: true });
  try {
    const respuesta = await fetch(`${base}${ruta}`, {
      method: 'GET',
      headers: { Accept: aceptar },
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
export const runs = (slug: string, s?: AbortSignal) => json<E['Manifest'][]>(`${novela(slug)}/runs`, s);

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
