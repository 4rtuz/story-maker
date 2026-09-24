// VER-12: la global por índice.
export const pedir = (url: string): Promise<Response> => globalThis['fetch'](url);
