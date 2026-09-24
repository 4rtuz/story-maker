// CA-03: fetch fuera de src/shared/api/.
export const pedir = (url: string): Promise<Response> => fetch(url);
