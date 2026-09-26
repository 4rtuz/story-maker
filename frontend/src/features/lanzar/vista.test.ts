// Lanzar como conversación (spec 0015, RF-09, RF-10): el chat pregunta, el resumen lanza la novela
// en el backend con un clic, y el tablero reparte los lanzamientos por fase sin enseñar registros
// (CA-11 a CA-13 en su parte unitaria).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { arrancar } from '../../app/rutas';
import { lanzar } from './vista';

const fetchEspia = vi.fn<typeof fetch>();
let parar: () => void;
let raiz: HTMLElement;

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', fetchEspia);
  fetchEspia.mockReset();
  location.hash = '#/lanzar';
  raiz = document.createElement('div');
  document.body.replaceChildren(raiz);
});

afterEach(() => {
  parar?.();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const cursor = { capitulo: 1, fase: 'escritura', ultimo_paso: null, intento: 1 };
const lanz = (slug: string, estado: string, extra: object = {}) => ({
  slug,
  estado,
  paso: 'capitulo 02',
  detalle: 'escritura, revisión y registro',
  actualizado: '2026-09-24T18:00:00Z',
  detener_pedido: false,
  registro: ['[18:00:00] /novela-continuar · sesión x'],
  ...extra,
});
const respuesta = (cuerpo: unknown, status = 200) => new Response(JSON.stringify(cuerpo), { status });

function api(rutas: Record<string, () => Response | Promise<Response>>) {
  fetchEspia.mockImplementation((url, opciones) => {
    const clave = `${opciones?.method ?? 'GET'} ${String(url).replace('http://127.0.0.1:8000', '')}`;
    const r = rutas[clave];
    return r ? Promise.resolve(r()) : Promise.resolve(respuesta({ detail: `sin ruta ${clave}` }, 500));
  });
}

const pedidas = () => fetchEspia.mock.calls.map(([url, o]) => `${o?.method} ${String(url).replace('http://127.0.0.1:8000', '')}`);

async function montar(): Promise<void> {
  parar = arrancar(raiz, () => lanzar()).detener;
  await vi.advanceTimersByTimeAsync(1000);
}

const boton = (texto: string) =>
  [...raiz.querySelectorAll('button')].find((b) => b.textContent?.trim().startsWith(texto)) as HTMLButtonElement;

async function pulsar(texto: string): Promise<void> {
  const b = boton(texto);
  if (!b) throw new Error(`no hay botón «${texto}»`);
  b.click();
  await vi.advanceTimersByTimeAsync(1000);
}

async function escribir(texto: string): Promise<void> {
  const entrada = raiz.querySelector<HTMLTextAreaElement>('.q-chat__texto');
  if (!entrada) throw new Error('no hay entrada de texto');
  entrada.value = texto;
  raiz.querySelector('form')?.dispatchEvent(new Event('submit', { cancelable: true }));
  await vi.advanceTimersByTimeAsync(1000);
}

const ultimaDelBot = () => [...raiz.querySelectorAll('.q-burbuja--bot')].at(-1)?.textContent ?? '';
const BASE = { 'GET /novelas': () => respuesta([{ slug: 'demo-24', cursor }]), 'GET /lanzamientos': () => respuesta([]) };

describe('Lanzar', () => {
  it('la conversación termina en un resumen que lanza con un clic, sin preguntar la extensión', async () => {
    const lanzada = lanz('faro-apagado', 'en_marcha', { paso: 'entorno' });
    let lanzadas: unknown[] = [];
    api({
      ...BASE,
      'GET /lanzamientos': () => respuesta(lanzadas),
      'POST /lanzamientos': () => ((lanzadas = [lanzada]), respuesta(lanzada, 202)),
    });
    await montar();
    expect(ultimaDelBot()).toContain('¿Es un regalo');
    await pulsar('No, es para mí');
    await escribir('Un faro apagado.');
    await pulsar('Noir');
    await pulsar('Omitir');
    expect(ultimaDelBot()).toContain('capítulos');
    await pulsar('10');
    expect(ultimaDelBot()).toContain('palabras');
    await escribir('30.000');
    await escribir('faro-apagado');
    expect(raiz.textContent).not.toMatch(/extensi[oó]n/i);
    expect(raiz.querySelector('.q-resumen')?.textContent).toContain('30.000');
    await pulsar('Lanzar novela');
    const post = fetchEspia.mock.calls.find(([, o]) => o?.method === 'POST');
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({
      slug: 'faro-apagado',
      idea: 'Género: noir.\n\nUn faro apagado.',
      capitulos: 10,
      palabras: 30000,
    });
    expect(ultimaDelBot()).toContain('En marcha');
    expect(raiz.querySelector('[data-columna="proceso"]')?.textContent).toContain('Faro apagado');
  });

  it('una respuesta inválida la explica el bot y no avanza (CA-12)', async () => {
    api(BASE);
    await montar();
    await pulsar('No, es para mí');
    await escribir('Un faro apagado.');
    await pulsar('Omitir');
    await pulsar('Omitir');
    await escribir('muchos');
    expect(raiz.querySelector('.q-burbuja--error')?.textContent).toContain('entero');
    expect(ultimaDelBot()).toContain('capítulos');
  });

  it('un nombre corto existente no se acepta (CA-13)', async () => {
    api(BASE);
    await montar();
    for (const paso of ['No, es para mí']) await pulsar(paso);
    await escribir('Un faro apagado.');
    await pulsar('Omitir');
    await pulsar('Omitir');
    await pulsar('10');
    await pulsar('30.000');
    await escribir('demo-24');
    expect(raiz.querySelector('.q-burbuja--error')?.textContent).toContain('ya existe una novela llamada demo-24');
    expect(pedidas().some((p) => p.startsWith('POST'))).toBe(false);
  });

  it('si el backend lo rechaza, el bot da su motivo y se puede reintentar', async () => {
    api({ ...BASE, 'POST /lanzamientos': () => respuesta({ detail: 'ya hay un lanzamiento en marcha: espera o detenlo' }, 409) });
    await montar();
    await pulsar('No, es para mí');
    await escribir('Un faro apagado.');
    await pulsar('Omitir');
    await pulsar('Omitir');
    await pulsar('10');
    await pulsar('30.000');
    await escribir('faro');
    await pulsar('Lanzar novela');
    expect(ultimaDelBot()).toContain('ya hay un lanzamiento en marcha');
    expect(boton('Lanzar novela').disabled).toBe(false);
  });

  it('el tablero reparte por fase, sin registro, y deja detener y reanudar (RF-10)', async () => {
    api({
      ...BASE,
      'GET /lanzamientos': () =>
        respuesta([lanz('uno', 'en_marcha'), lanz('dos', 'fallido'), lanz('tres', 'detenido'), lanz('cuatro', 'terminado', { paso: 'auditoria' })]),
      'POST /lanzamientos/uno/detener': () => respuesta(lanz('uno', 'en_marcha', { detener_pedido: true }), 202),
      'POST /lanzamientos/dos/reanudar': () => respuesta(lanz('dos', 'en_marcha', { paso: 'entorno' }), 202),
    });
    await montar();
    const columna = (clave: string) => raiz.querySelector(`[data-columna="${clave}"]`)?.textContent ?? '';
    expect(columna('proceso')).toContain('Escribiendo el capítulo 2');
    expect(columna('bloqueada')).toContain('Dos');
    expect(columna('pausa')).toContain('Tres');
    expect(columna('terminada')).toContain('Lista para leer');
    expect(raiz.textContent).not.toContain('/novela-continuar');
    expect(raiz.textContent).not.toContain('Slugs en uso');
    boton('Detener').click();
    raiz.querySelector<HTMLButtonElement>('[data-columna="bloqueada"] button')?.click();
    await vi.advanceTimersByTimeAsync(0);
    expect(pedidas()).toEqual(expect.arrayContaining(['POST /lanzamientos/uno/detener', 'POST /lanzamientos/dos/reanudar']));
    expect(raiz.textContent).toContain('se pausará al terminarlo');
  });

  it('con la API caída, el aviso (CA-58)', async () => {
    fetchEspia.mockRejectedValue(new TypeError('Failed to fetch'));
    await montar();
    expect(raiz.querySelector('[role="alert"]')?.textContent).toContain('API no disponible');
  });
});
