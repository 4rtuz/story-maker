// El cliente de la API: el único módulo del panel que sale a la red (RF-03).

/** `VITE_API_URL`, o la de uvicorn por defecto (RF-01, D15). */
export function urlBase(entorno: { VITE_API_URL?: string } = import.meta.env): string {
  return entorno.VITE_API_URL || 'http://127.0.0.1:8000';
}
