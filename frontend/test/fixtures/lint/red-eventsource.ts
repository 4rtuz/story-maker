// CA-03: SSE, que D2 descarta.
export const eventos = (url: string): EventSource => new EventSource(url);
