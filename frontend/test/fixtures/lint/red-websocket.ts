// CA-03: un segundo transporte, que D2 descarta.
export const canal = (url: string): WebSocket => new WebSocket(url);
