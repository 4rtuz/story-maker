// El fallo de una petición a la API, con el texto que ve el operador (RF-04, spec 0004 §8.4).

export type TipoDeError = 'red' | 'tiempo' | 'http';

export class ErrorDeApi extends Error {
  constructor(
    readonly tipo: TipoDeError,
    readonly detalle: string,
    readonly status?: number,
  ) {
    super(detalle);
    this.name = 'ErrorDeApi';
  }
}

export const PLAZO_MS = 5_000;
export const ORIGEN_DEL_PANEL = 'http://localhost:5173';

export function deRed(url: string, origen: string = globalThis.location?.origin ?? ''): ErrorDeApi {
  // El CORS solo admite localhost:5173: desde otro origen todo falla por red y parecería una caída.
  const pista = origen && origen !== ORIGEN_DEL_PANEL ? `; abre el panel en ${ORIGEN_DEL_PANEL}` : '';
  return new ErrorDeApi('red', `API no disponible en ${url}${pista}`);
}

export function deTiempo(): ErrorDeApi {
  return new ErrorDeApi('tiempo', 'la API no respondió en 5 s');
}

/** El `detail` de FastAPI: una cadena, o la lista de errores de validación de un 422. */
export function deHttp(status: number, cuerpo: string): ErrorDeApi {
  let detail: unknown;
  try {
    detail = (JSON.parse(cuerpo) as { detail?: unknown } | null)?.detail;
  } catch {
    detail = undefined;
  }
  const mensajes = Array.isArray(detail)
    ? detail.map((d: { msg?: unknown }) => d?.msg).filter((m): m is string => typeof m === 'string')
    : [];
  const detalle =
    typeof detail === 'string' && detail
      ? detail
      : mensajes.length
        ? mensajes.join('; ')
        : `la API respondió ${status}`;
  return new ErrorDeApi('http', detalle, status);
}
