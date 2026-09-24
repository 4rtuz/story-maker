// VER-12 y VAL-35: una petición que no pasa por el cliente.
export const avisar = (url: string): boolean => navigator.sendBeacon(url);
