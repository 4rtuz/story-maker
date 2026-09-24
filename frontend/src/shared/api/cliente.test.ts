import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from './cliente';
import { urlBase } from './cliente';
import { ErrorDeApi } from './errores';

describe('URL de la API (CA-01)', () => {
  it('sin VITE_API_URL, la de uvicorn por defecto', () => {
    expect(urlBase({})).toBe('http://127.0.0.1:8000');
    expect(urlBase()).toBe('http://127.0.0.1:8000');
  });

  it('con VITE_API_URL, esa', () => {
    expect(urlBase({ VITE_API_URL: 'http://127.0.0.1:9000' })).toBe('http://127.0.0.1:9000');
  });
});

const espia = vi.fn<typeof fetch>();
const json = (cuerpo: unknown, status = 200): Response =>
  new Response(JSON.stringify(cuerpo), { status, headers: { 'Content-Type': 'application/json' } });

beforeEach(() => {
  espia.mockReset();
  vi.stubGlobal('fetch', espia);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const RUN = 'r-20260107-0900';
const LLAMADAS: [string, () => Promise<unknown>, string][] = [
  ['novelas', () => api.novelas(), '/novelas'],
  ['estado', () => api.estado('demo-24'), '/novelas/demo-24/estado'],
  ['capitulos', () => api.capitulos('demo-24'), '/novelas/demo-24/capitulos'],
  ['capitulo', () => api.capitulo('demo-24', 3), '/novelas/demo-24/capitulos/3'],
  ['manifiesto', () => api.manifiesto('demo-24', RUN), `/novelas/demo-24/runs/${RUN}`],
  ['config', () => api.config('demo-24'), '/novelas/demo-24/config'],
  ['escaleta', () => api.escaleta('demo-24'), '/novelas/demo-24/escaleta'],
  ['checkpoint', () => api.checkpoint('demo-24'), '/novelas/demo-24/checkpoint'],
  ['runs', () => api.runs('demo-24'), '/novelas/demo-24/runs'],
  ['log', () => api.log('demo-24', RUN, 120), `/novelas/demo-24/runs/${RUN}/log?desde=120`],
];

describe('cada GET (CA-03)', () => {
  it.each(LLAMADAS)('%s sale con GET y solo la cabecera Accept', async (_, llamada, ruta) => {
    espia.mockResolvedValue(json(null));
    await llamada();
    expect(espia).toHaveBeenCalledOnce();
    const [url, opciones] = espia.mock.calls[0] ?? [];
    expect(url).toBe(`http://127.0.0.1:8000${ruta}`);
    expect(opciones?.method).toBe('GET');
    expect(Object.keys(opciones?.headers ?? {})).toEqual(['Accept']);
    expect(opciones?.body).toBeUndefined();
  });

  it('el capítulo llega como texto', async () => {
    espia.mockResolvedValue(new Response('---\ncapitulo: 3\n---\nCuerpo', { status: 200 }));
    expect(await api.capitulo('demo-24', 3)).toBe('---\ncapitulo: 3\n---\nCuerpo');
  });
});

async function fallo(promesa: Promise<unknown>): Promise<ErrorDeApi> {
  const error = await promesa.then(
    () => null,
    (e: unknown) => e,
  );
  expect(error).toBeInstanceOf(ErrorDeApi);
  return error as ErrorDeApi;
}

describe('fallos (CA-04, parte unitaria)', () => {
  it('un 404 trae el detail de la respuesta', async () => {
    espia.mockResolvedValue(json({ detail: 'no existe la novela demo-24' }, 404));
    const error = await fallo(api.estado('demo-24'));
    expect(error).toMatchObject({ tipo: 'http', status: 404, detalle: 'no existe la novela demo-24' });
  });

  it('un 422 con la lista de errores de FastAPI da su mensaje', async () => {
    espia.mockResolvedValue(json({ detail: [{ msg: 'Input should be greater than or equal to 0' }] }, 422));
    expect((await fallo(api.log('demo-24', RUN, 0))).detalle).toBe(
      'Input should be greater than or equal to 0',
    );
  });

  it('un 500 sin cuerpo da el código', async () => {
    espia.mockResolvedValue(new Response('', { status: 500 }));
    expect((await fallo(api.estado('demo-24'))).detalle).toBe('la API respondió 500');
  });

  it('la red caída da «API no disponible en <url>»', async () => {
    espia.mockRejectedValue(new TypeError('Failed to fetch'));
    const error = await fallo(api.novelas());
    expect(error).toMatchObject({ tipo: 'red', detalle: 'API no disponible en http://127.0.0.1:8000' });
  });

  it('pasados 5 s, «la API no respondió en 5 s», con el reloj simulado (VER-11)', async () => {
    vi.useFakeTimers();
    espia.mockImplementation(
      (_, opciones) =>
        new Promise((_, rechazar) =>
          opciones?.signal?.addEventListener('abort', () => rechazar(opciones.signal?.reason)),
        ),
    );
    const promesa = fallo(api.estado('demo-24'));
    await vi.advanceTimersByTimeAsync(4_999);
    expect(espia.mock.calls[0]?.[1]?.signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(await promesa).toMatchObject({ tipo: 'tiempo', detalle: 'la API no respondió en 5 s' });
  });

  it('abortar la vista no es un error de la API: la promesa rechaza con AbortError', async () => {
    const vista = new AbortController();
    espia.mockImplementation(
      (_, opciones) =>
        new Promise((_, rechazar) =>
          opciones?.signal?.addEventListener('abort', () =>
            rechazar(new DOMException('abortada', 'AbortError')),
          ),
        ),
    );
    const promesa = api.estado('demo-24', vista.signal);
    vista.abort();
    await expect(promesa).rejects.toMatchObject({ name: 'AbortError' });
  });
});

describe('respuestas con tratamiento propio (RF-19, RF-22)', () => {
  it('el 404 de la escaleta es «sin escaleta», no un error', async () => {
    espia.mockResolvedValue(json({ detail: 'falta plan/escaleta.md' }, 404));
    expect(await api.escaleta('recien-creada')).toBeNull();
  });

  it('el 416 del log es «vuelve a desde=0», no un error', async () => {
    espia.mockResolvedValue(json({ detail: 'desde 9 pasa del tamaño del log (4)' }, 416));
    expect(await api.log('demo-24', RUN, 9)).toBeNull();
  });
});
