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
  });

  it('sin estantería 3D ni lista de capítulos: portada con su ilustración, índice y ficha (RF-12)', async () => {
    servirLectura();
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('canvas, .q-escena, .q-volumenes')).toBeNull();
    const portada = raiz.querySelector('[data-testid="portada"]');
    expect(portada?.querySelector('img')?.getAttribute('src')).toBe('http://127.0.0.1:8000/novelas/demo-24/portada');
    expect(portada?.querySelector('[data-testid="portada-empezar"]')?.textContent).toContain('Empezar a leer');
    expect(portada?.textContent).toContain('Noir · 24 capítulos');
  });

  it('esqueleto mientras llegan los datos (CA-58)', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    montar('#/novelas/demo-24/lectura');
    expect(raiz.querySelectorAll('.q-esqueleto').length).toBeGreaterThanOrEqual(2);
  });

  it('sin capítulos cerrados, su texto de vacío (CA-58)', async () => {
    servirLectura({
      '/checkpoint': json(null),
      '/capitulos': json([]),
      '/libro': json({ titulo: 'demo-24', dedicatoria: null, capitulos: [], personajes: [], lugares: [] }),
    });
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('ningún capítulo cerrado todavía');
    expect(raiz.querySelector('[role="alert"]')).toBeNull();
  });

  it('ante un fallo, el aviso y los datos anteriores conservados (CA-58)', async () => {
    servirLectura();
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    servirLectura({ '/libro': json({ detail: 'el capítulo 8 no valida su frontmatter' }, 404) });
    await vi.advanceTimersByTimeAsync(10_001);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toBe('el capítulo 8 no valida su frontmatter');
    expect(raiz.querySelectorAll('[data-testid="indice-capitulo"]')).toHaveLength(7);
  });

  it('la tarjeta Libro: portada con dedicatoria, índice de los cerrados y ficha enlazada', async () => {
    servirLectura();
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    const por = (id: string) => [...raiz.querySelectorAll<HTMLElement>(`[data-testid="${id}"]`)];
    expect(por('portada-dedicatoria')[0]?.textContent).toBe('Para Aurora Ficticia, en el día de su boda.');
    expect(por('indice-capitulo')).toHaveLength(7);
    expect(por('ficha-enlace').map((a) => a.dataset.destino)).toEqual(['1', '3']);
  });

  it('un enlace de la ficha abre el lector de ese capítulo', async () => {
    const pedidas = servirLectura();
    montar('#/novelas/demo-24/lectura');
    await vi.advanceTimersByTimeAsync(0);
    const enlace = raiz.querySelector('[data-testid="ficha-enlace"][data-destino="3"]');
    // jsdom no navega al pulsar un enlace: se sigue su href a mano; el clic real lo cubre e2e/libro.spec.ts.
    location.hash = enlace?.getAttribute('href') ?? '';
    window.dispatchEvent(new HashChangeEvent('hashchange'));
    await vi.advanceTimersByTimeAsync(0);
    expect(pedidas).toContain('/capitulos/3');
    expect(raiz.querySelector('[data-testid="lector-titulo"]')?.textContent).toBe('Capítulo tres');
  });
  describe('el lector como un libro (spec 0015)', () => {
    const pulsar = async (nombre: string) => {
      raiz.querySelector<HTMLButtonElement>(`[role="dialog"] button[aria-label="${nombre}"]`)?.click();
      await vi.advanceTimersByTimeAsync(0);
    };

    it('junto a «Empezar a leer», «Descargar PDF» apunta al PDF de la API', async () => {
      servirLectura();
      montar('#/novelas/demo-24/lectura');
      await vi.advanceTimersByTimeAsync(0);
      const pdf = raiz.querySelector<HTMLAnchorElement>('[data-testid="portada-pdf"]');
      expect(pdf?.textContent).toContain('Descargar PDF');
      expect(pdf?.getAttribute('href')).toBe('http://127.0.0.1:8000/novelas/demo-24/pdf');
      expect(pdf?.parentElement).toBe(raiz.querySelector('[data-testid="portada-empezar"]')?.parentElement);
    });

    it('el capítulo 1 se abre por la portada, con su ilustración y el título; los demás no', async () => {
      servirLectura();
      montar('#/novelas/demo-24/lectura/1');
      await vi.advanceTimersByTimeAsync(0);
      const portada = dialogo()?.querySelector('.q-lector__portada');
      expect(portada?.querySelector('img')?.getAttribute('src')).toBe('http://127.0.0.1:8000/novelas/demo-24/portada');
      expect(portada?.textContent).toContain('Demo 24');
      expect(portada?.textContent).toContain('Para Aurora Ficticia');
      location.hash = '#/novelas/demo-24/lectura/3';
      await vi.advanceTimersByTimeAsync(0);
      expect(dialogo()?.querySelector('.q-lector__portada')).toBeNull();
    });

    it('el fondo se elige entre papel, sepia y noche, y se mantiene al cambiar de capítulo', async () => {
      servirLectura();
      montar('#/novelas/demo-24/lectura/3');
      await vi.advanceTimersByTimeAsync(0);
      expect(dialogo()?.getAttribute('data-tema')).toBe('papel');
      await pulsar('Fondo sepia');
      expect(dialogo()?.getAttribute('data-tema')).toBe('sepia');
      expect(dialogo()?.querySelector('[aria-label="Fondo sepia"]')?.getAttribute('aria-pressed')).toBe('true');
      await pulsar('Capítulo siguiente');
      expect(location.hash).toBe('#/novelas/demo-24/lectura/4');
      expect(dialogo()?.getAttribute('data-tema')).toBe('sepia');
      await pulsar('Fondo papel'); // deja el tema como estaba para los demás tests
    });

    it('la letra crece y mengua entre sus límites', async () => {
      servirLectura();
      montar('#/novelas/demo-24/lectura/3');
      await vi.advanceTimersByTimeAsync(0);
      const tamano = () => (dialogo() as HTMLElement | null)?.style.getPropertyValue('--tamano-lectura');
      const inicial = tamano();
      await pulsar('Aumentar letra');
      expect(parseFloat(tamano() ?? '')).toBeGreaterThan(parseFloat(inicial ?? ''));
      for (let i = 0; i < 20; i++) await pulsar('Reducir letra');
      expect(tamano()).toBe('14px');
      for (let i = 0; i < 20; i++) await pulsar('Aumentar letra');
      expect(tamano()).toBe('26px');
      for (let i = 0; i < 20; i++) await pulsar('Reducir letra');
      for (let i = 0; i < 2; i++) await pulsar('Aumentar letra'); // vuelve a 18px
    });
  });

  describe('libro abierto', () => {
    const pulsarEn = (key: string) =>
      raiz.querySelector('[role="dialog"]')?.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));
    const boton = (etiqueta: string) => raiz.querySelector<HTMLButtonElement>(`[role="dialog"] button[aria-label="${etiqueta}"]`);
    /** jsdom no maqueta: el texto se finge de `pliegos` pliegos del ancho de la hoja. */
    const paginar = (pliegos: number) => {
      const texto = raiz.querySelector('.q-lector__texto')!;
      Object.defineProperty(texto, 'clientWidth', { value: 500, configurable: true });
      Object.defineProperty(texto, 'scrollWidth', { value: 500 * pliegos, configurable: true });
    };
    const pliego = () => raiz.querySelector<HTMLElement>('[data-pliego]')?.dataset.pliego;

    it('flechas de capítulo: botones y ← →, sin anterior en el primero ni siguiente en el último cerrado', async () => {
      servirLectura();
      montar('#/novelas/demo-24/lectura/3');
      await vi.advanceTimersByTimeAsync(0);
      boton('Capítulo siguiente')?.click();
      await vi.advanceTimersByTimeAsync(0);
      expect(location.hash).toBe('#/novelas/demo-24/lectura/4');
      pulsarEn('ArrowLeft');
      await vi.advanceTimersByTimeAsync(0);
      expect(location.hash).toBe('#/novelas/demo-24/lectura/3');
      location.hash = '#/novelas/demo-24/lectura/1';
      await vi.advanceTimersByTimeAsync(0);
      expect(boton('Capítulo anterior')).toBeNull();
      expect(boton('Capítulo siguiente')).not.toBeNull();
      location.hash = '#/novelas/demo-24/lectura/7';
      await vi.advanceTimersByTimeAsync(0);
      expect(boton('Capítulo siguiente')).toBeNull();
      expect(boton('Capítulo anterior')).not.toBeNull();
    });

    it('la página derecha pasa pliego y, al final, lleva al capítulo siguiente', async () => {
      servirLectura();
      montar('#/novelas/demo-24/lectura/3');
      await vi.advanceTimersByTimeAsync(0);
      paginar(2);
      expect(pliego()).toBe('0');
      boton('Página siguiente')?.click();
      expect(pliego()).toBe('1');
      expect(location.hash).toBe('#/novelas/demo-24/lectura/3');
      boton('Página siguiente')?.click();
      await vi.advanceTimersByTimeAsync(0);
      expect(location.hash).toBe('#/novelas/demo-24/lectura/4');
      expect(pliego()).toBe('0');
    });

    it('la página izquierda retrocede y, al principio, vuelve al capítulo anterior', async () => {
      servirLectura();
      montar('#/novelas/demo-24/lectura/3');
      await vi.advanceTimersByTimeAsync(0);
      paginar(3);
      boton('Página siguiente')?.click();
      boton('Página anterior')?.click();
      expect(pliego()).toBe('0');
      boton('Página anterior')?.click();
      await vi.advanceTimersByTimeAsync(0);
      expect(location.hash).toBe('#/novelas/demo-24/lectura/2');
    });
  });
});
