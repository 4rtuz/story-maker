// Lanzar: el formulario lanza la novela en el backend, sin órdenes que copiar, y la lista de
// lanzamientos permite detener y reanudar (CA-11 a CA-13, CA-58 en su parte unitaria).
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

/** Una API falsa por ruta y método; devuelve las peticiones que recibió. */
function api(rutas: Record<string, () => Response | Promise<Response>>) {
  fetchEspia.mockImplementation((url, opciones) => {
    const clave = `${opciones?.method ?? 'GET'} ${String(url).replace('http://127.0.0.1:8000', '')}`;
    const r = rutas[clave];
    return r ? Promise.resolve(r()) : Promise.resolve(respuesta({ detail: `sin ruta ${clave}` }, 500));
  });
}

const pedidas = () =>
  fetchEspia.mock.calls.map(([url, o]) => `${o?.method} ${String(url).replace('http://127.0.0.1:8000', '')}`);

async function montar(): Promise<void> {
  parar = arrancar(raiz, () => lanzar()).detener;
  await vi.advanceTimersByTimeAsync(0);
}

function rellenar(campos: Record<string, string>): void {
  for (const [id, valor] of Object.entries(campos)) {
    const control = raiz.querySelector<HTMLInputElement | HTMLTextAreaElement>(`#${id}`);
    if (!control) throw new Error(`falta el campo ${id}`);
    control.value = valor;
    control.dispatchEvent(new Event('input', { bubbles: true }));
  }
}

const boton = (texto: string) =>
  [...raiz.querySelectorAll('button')].find((b) => b.textContent?.startsWith(texto)) as HTMLButtonElement;

const BASE = { 'GET /novelas': () => respuesta([{ slug: 'demo-24', cursor }]), 'GET /lanzamientos': () => respuesta([]) };

describe('Lanzar', () => {
  it('lanza en el backend con un clic, sin nada que copiar', async () => {
    api({ ...BASE, 'POST /lanzamientos': () => respuesta(lanz('nueva-prueba', 'en_marcha', { paso: 'entorno' }), 202) });
    await montar();
    rellenar({ 'lanzar-slug': 'nueva-prueba', 'lanzar-idea': 'Un faro apagado.', 'lanzar-capitulos': '3', 'lanzar-palabras': '9000' });
    boton('Lanzar novela').click();
    await vi.advanceTimersByTimeAsync(0);
    const post = fetchEspia.mock.calls.find(([, o]) => o?.method === 'POST');
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ slug: 'nueva-prueba', idea: 'Un faro apagado.', capitulos: 3, palabras: 9000 });
    expect(raiz.querySelector('.q-lanzamiento')?.textContent).toContain('nueva-prueba');
    expect(raiz.querySelector('.q-lanzamiento')?.textContent).toContain('en marcha');
    expect(boton('Copiar')).toBeUndefined();
    expect(raiz.textContent).not.toContain('/novela-nueva');
  });

  it('sin capítulos ni palabras, el cuerpo no los lleva', async () => {
    api({ ...BASE, 'POST /lanzamientos': () => respuesta(lanz('nueva-prueba', 'en_marcha'), 202) });
    await montar();
    rellenar({ 'lanzar-slug': 'nueva-prueba', 'lanzar-idea': 'Un faro apagado.' });
    boton('Lanzar novela').click();
    await vi.advanceTimersByTimeAsync(0);
    const post = fetchEspia.mock.calls.find(([, o]) => o?.method === 'POST');
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ slug: 'nueva-prueba', idea: 'Un faro apagado.' });
  });

  it('un campo inválido da su motivo y no lanza nada (CA-12)', async () => {
    api(BASE);
    await montar();
    rellenar({ 'lanzar-slug': 'Nueva_Prueba', 'lanzar-idea': '   ' });
    boton('Lanzar novela').click();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelectorAll('[aria-invalid="true"]')).toHaveLength(2);
    expect(pedidas().some((p) => p.startsWith('POST'))).toBe(false);
  });

  it('un slug existente no lanza (CA-13)', async () => {
    api(BASE);
    await montar();
    rellenar({ 'lanzar-slug': 'demo-24', 'lanzar-idea': 'Un faro apagado.' });
    boton('Lanzar novela').click();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('ya existe una novela demo-24');
    expect(pedidas().some((p) => p.startsWith('POST'))).toBe(false);
  });

  it('si el backend lo rechaza, se ve su motivo', async () => {
    api({ ...BASE, 'POST /lanzamientos': () => respuesta({ detail: 'ya hay un lanzamiento en marcha: espera o detenlo' }, 409) });
    await montar();
    rellenar({ 'lanzar-slug': 'nueva-prueba', 'lanzar-idea': 'Un faro apagado.' });
    boton('Lanzar novela').click();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('.q-lanzar__resultado-envio')?.textContent).toContain('ya hay un lanzamiento en marcha');
    expect(boton('Lanzar novela').disabled).toBe(false);
  });

  it('en marcha se detiene; parado, fallido o interrumpido se reanuda', async () => {
    api({
      ...BASE,
      'GET /lanzamientos': () => respuesta([lanz('uno', 'en_marcha'), lanz('dos', 'fallido', { detalle: 'necesita una decisión humana' })]),
      'POST /lanzamientos/uno/detener': () => respuesta(lanz('uno', 'en_marcha', { detener_pedido: true }), 202),
      'POST /lanzamientos/dos/reanudar': () => respuesta(lanz('dos', 'en_marcha', { paso: 'entorno' }), 202),
    });
    await montar();
    const [uno, dos] = [...raiz.querySelectorAll('.q-lanzamiento')];
    expect(uno?.textContent).toContain('capitulo 02');
    expect(dos?.textContent).toContain('necesita una decisión humana');
    expect(dos?.querySelector('.q-lanzamiento__registro')?.textContent).toContain('/novela-continuar');
    boton('Detener').click();
    boton('Reanudar').click();
    await vi.advanceTimersByTimeAsync(0);
    expect(pedidas()).toEqual(expect.arrayContaining(['POST /lanzamientos/uno/detener', 'POST /lanzamientos/dos/reanudar']));
    expect(raiz.textContent).toContain('se detendrá tras el capítulo en curso');
  });

  it('esqueleto, vacío y error de GET /novelas (CA-58)', async () => {
    fetchEspia.mockReturnValue(new Promise(() => {}));
    parar = arrancar(raiz, () => lanzar()).detener;
    expect(raiz.querySelectorAll('.q-esqueleto').length).toBeGreaterThan(0);
    parar();
    api({ 'GET /novelas': () => respuesta([]), 'GET /lanzamientos': () => respuesta([]) });
    await montar();
    expect(raiz.textContent).toContain('todavía no hay novelas: lanza la primera');
    parar();
    fetchEspia.mockReset();
    fetchEspia.mockRejectedValue(new TypeError('Failed to fetch'));
    parar = arrancar(raiz, () => lanzar()).detener;
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toContain('API no disponible');
  });
});
