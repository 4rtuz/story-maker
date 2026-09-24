// La cáscara de Lanzar: formulario, orden, copiar con alternativa y estados de GET /novelas
// (CA-11, CA-13, CA-58 en su parte unitaria, RF-16). Ningún control ejecuta nada.
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

const novelas = (slugs: string[]) =>
  new Response(JSON.stringify(slugs.map((slug) => ({ slug, cursor: { capitulo: 1, fase: 'escritura', ultimo_paso: null, intento: 1 } }))));

async function montar(respuesta: Promise<Response> | Response = novelas(['demo-24'])): Promise<void> {
  fetchEspia.mockReturnValue(Promise.resolve(respuesta));
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
const orden = () => raiz.querySelector('.q-orden__texto')?.textContent ?? '';

describe('Lanzar', () => {
  it('genera la orden, con las de la sesión debajo, y Copiar la escribe (CA-11, CA-15)', async () => {
    const escribir = vi.fn(() => Promise.resolve());
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText: escribir } });
    await montar();
    expect(boton('Copiar').disabled).toBe(true);
    rellenar({ 'lanzar-slug': 'nueva-prueba', 'lanzar-idea': 'Un faro apagado.', 'lanzar-capitulos': '3', 'lanzar-palabras': '9000' });
    boton('Generar orden').click();
    expect(orden()).toBe("/novela-nueva nueva-prueba --idea 'Un faro apagado.' --capitulos 3 --palabras 9000");
    expect(raiz.textContent).toContain('/novela-continuar nueva-prueba');
    expect(boton('Copiar').disabled).toBe(false);
    boton('Copiar').click();
    await vi.advanceTimersByTimeAsync(0);
    expect(escribir).toHaveBeenCalledWith(orden());
  });

  it('con el portapapeles denegado, el texto queda seleccionado con «pulsa Ctrl+C para copiar»', async () => {
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText: () => Promise.reject(new Error('denegado')) } });
    await montar();
    rellenar({ 'lanzar-slug': 'nueva-prueba', 'lanzar-idea': 'Un faro apagado.' });
    boton('Generar orden').click();
    boton('Copiar').click();
    await vi.advanceTimersByTimeAsync(0);
    const campo = raiz.querySelector<HTMLTextAreaElement>('textarea[readonly]');
    expect(campo?.value).toBe(orden());
    expect(document.activeElement).toBe(campo);
    expect([campo?.selectionStart, campo?.selectionEnd]).toEqual([0, orden().length]);
    expect(raiz.textContent).toContain('pulsa Ctrl+C para copiar');
  });

  it('un campo inválido da su motivo y no hay orden (CA-12)', async () => {
    await montar();
    rellenar({ 'lanzar-slug': 'Nueva_Prueba', 'lanzar-idea': '   ' });
    boton('Generar orden').click();
    expect(orden()).toBe('');
    expect(raiz.querySelectorAll('[aria-invalid="true"]')).toHaveLength(2);
  });

  it('un slug existente no da orden (CA-13)', async () => {
    await montar();
    rellenar({ 'lanzar-slug': 'demo-24', 'lanzar-idea': 'Un faro apagado.' });
    boton('Generar orden').click();
    expect(orden()).toBe('');
    expect(raiz.textContent).toContain('ya existe una novela demo-24: novela nueva saldrá con 1 sin tocar nada');
  });

  it('sin respuesta de GET /novelas, la orden sale con el aviso de D43', async () => {
    await montar(new Promise(() => {}));
    rellenar({ 'lanzar-slug': 'demo-24', 'lanzar-idea': 'Un faro apagado.' });
    boton('Generar orden').click();
    expect(orden()).toContain('/novela-nueva demo-24');
    expect(raiz.textContent).toContain('no se ha podido comprobar si el slug ya existe');
  });

  it('esqueleto, vacío y error de GET /novelas (CA-58)', async () => {
    fetchEspia.mockReturnValue(new Promise(() => {}));
    parar = arrancar(raiz, () => lanzar()).detener;
    expect(raiz.querySelectorAll('.q-esqueleto').length).toBeGreaterThan(0);
    parar();
    await montar(novelas([]));
    expect(raiz.textContent).toContain('todavía no hay novelas: lanza la primera');
    parar();
    fetchEspia.mockRejectedValue(new TypeError('Failed to fetch'));
    parar = arrancar(raiz, () => lanzar()).detener;
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toContain('API no disponible');
  });

  it('solo pide GET /novelas y ningún control envía nada (RF-16)', async () => {
    await montar();
    rellenar({ 'lanzar-slug': 'nueva-prueba', 'lanzar-idea': 'Un faro apagado.' });
    boton('Generar orden').click();
    await vi.advanceTimersByTimeAsync(30_000);
    expect(new Set(fetchEspia.mock.calls.map(([url]) => String(url)))).toEqual(
      new Set(['http://127.0.0.1:8000/novelas']),
    );
    expect(raiz.querySelector('form[action], a[download]')).toBeNull();
    expect([...raiz.querySelectorAll('button')].every((b) => b.type === 'button')).toBe(true);
  });
});
