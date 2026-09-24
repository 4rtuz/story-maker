// La cáscara de Lectura contra el cliente real con fetch espiado: CA-27, CA-10 y CA-58 en su
// parte unitaria, y VAL-7 (el capítulo no se pide antes de conocer el checkpoint).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { arrancar } from '../../app/rutas';
import { lectura } from './vista';
import { json, servirLectura } from './servir-lectura.test-util';

let parar: (() => void) | undefined;
let raiz: HTMLElement;

beforeEach(() => {
  vi.useFakeTimers();
  raiz = document.createElement('div');
  document.body.replaceChildren(raiz);
});

afterEach(() => {
  parar?.();
  parar = undefined;
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function montar(hash: string): void {
  location.hash = hash;
  parar = arrancar(raiz, (ruta, navegar) => lectura(ruta as { vista: 'lectura'; slug: string }, navegar)).detener;
}

const dialogo = () => raiz.querySelector('[role="dialog"]');

describe('Lectura', () => {
  it('el 8 con checkpoint 7: «capítulo no disponible todavía» sin pedirlo (CA-27)', async () => {
    const pedidas = servirLectura();
    montar('#/novelas/demo-24/lectura/8');
    await vi.advanceTimersByTimeAsync(10_000);
    expect(dialogo()?.textContent).toContain('capítulo no disponible todavía');
    expect(pedidas).not.toContain('/capitulos/8');
  });

  it('con el checkpoint retrasado, el 3 se pide solo después de conocerlo (VAL-7)', async () => {
    let soltar: (r: Response) => void = () => {};
    const pedidas = servirLectura({ '/checkpoint': () => new Promise((r) => (soltar = r)) });
    montar('#/novelas/demo-24/lectura/3');
    await vi.advanceTimersByTimeAsync(0);
    expect(pedidas).not.toContain('/capitulos/3');
    soltar(new Response(JSON.stringify({ capitulo: 7 })));
    await vi.advanceTimersByTimeAsync(0);
    expect(pedidas).toContain('/capitulos/3');
  });

  it('una recarga con /lectura/3 reabre el 3 con su título (CA-10)', async () => {
    const pedidas = servirLectura();
    montar('#/novelas/demo-24/lectura/3');
    await vi.advanceTimersByTimeAsync(0);
    expect(pedidas).toContain('/capitulos/3');
    expect(dialogo()?.querySelector('h2')?.textContent).toBe('Capítulo tres');
    expect(raiz.querySelector('[aria-current="true"]')?.getAttribute('data-capitulo')).toBe('3');
  });

  it('lista con el estado también como texto y 24 volúmenes', async () => {
    servirLectura();
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    const items = [...raiz.querySelectorAll('.q-volumenes [data-capitulo]')];
    expect(items).toHaveLength(24);
    expect(items[0]?.textContent).toContain('cerrado');
    expect(items[7]?.textContent).toContain('en curso');
    expect(items[8]?.textContent).toContain('pendiente');
    expect(raiz.querySelector('[data-volumenes]')?.getAttribute('data-volumenes')).toBe('24');
  });

  it('esqueleto mientras llegan los datos (CA-58)', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    montar('#/novelas/demo-24/lectura');
    expect(raiz.querySelector('.q-banner__titular')?.textContent).toBe('demo-24');
    expect(raiz.querySelectorAll('.q-esqueleto').length).toBeGreaterThanOrEqual(2);
  });

  it('sin capítulos cerrados, su texto de vacío (CA-58)', async () => {
    servirLectura({ '/checkpoint': json(null), '/capitulos': json([]), '/escaleta': json({ detail: 'x' }, 404) });
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('ningún capítulo cerrado todavía');
    expect(raiz.querySelector('[role="alert"]')).toBeNull();
    expect(raiz.querySelectorAll('.q-volumenes [data-capitulo]')).toHaveLength(24);
  });

  it('ante un fallo, el aviso y los datos anteriores conservados (CA-58)', async () => {
    servirLectura();
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    servirLectura({ '/capitulos': json({ detail: 'el capítulo 8 no valida su frontmatter' }, 404) });
    await vi.advanceTimersByTimeAsync(10_001);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toBe('el capítulo 8 no valida su frontmatter');
    expect(raiz.querySelectorAll('.q-volumenes [data-capitulo]')).toHaveLength(24);
    expect(raiz.querySelectorAll('.q-volumenes [data-capitulo]')[7]?.textContent).toContain('en curso');
  });
});
