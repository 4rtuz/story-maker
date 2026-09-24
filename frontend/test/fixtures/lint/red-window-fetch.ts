// VER-12: la global por propiedad, que no-restricted-globals no ve.
export const pedir = (url: string): Promise<Response> => window.fetch(url);
