// CA-09, y CA-07 y CA-10 en su parte unitaria: rutas por hash validadas antes de cualquier
// petición, sin normalizar, y una vista montada cada vez.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { arrancar, hashDe, interpretar, type Montador, type Vista } from './rutas';

describe('interpretar', () => {
  it.each([
    ['', { vista: 'inicio' }],
    ['#/', { vista: 'inicio' }],
    ['#/lanzar', { vista: 'lanzar' }],
    ['#/novelas/demo-24/progreso', { vista: 'progreso', slug: 'demo-24' }],
    ['#/novelas/demo-24/lectura', { vista: 'lectura', slug: 'demo-24' }],
    ['#/novelas/demo-24/lectura/3', { vista: 'lectura', slug: 'demo-24', capitulo: 3 }],
    ['#/novelas/demo-24/lectura/999', { vista: 'lectura', slug: 'demo-24', capitulo: 999 }],
  ])('%s', (hash, ruta) => {
    expect(interpretar(hash)).toEqual(ruta);
  });

  it.each([
    '#/novelas/..%2Fetc/progreso',
    '#/novelas/Demo/progreso',
    '#/novelas/demo_24/progreso',
    '#/novelas//progreso',
    '#/novelas/demo-24%2F..%2F/progreso',
    '#/novelas/demo-24/lectura/0',
    '#/novelas/demo-24/lectura/07',
    '#/novelas/demo-24/lectura/+3',
    '#/novelas/demo-24/lectura/1000',
    '#/novelas/demo-24/lectura/-1',
    '#/novelas/demo-24/lectura/2.5',
    '#/novelas/demo-24/lectura/abc',
    '#/novelas/demo-24/lectura/%203',
    '#/novelas/demo-24',
    '#/novelas/demo-24/progreso/3',
    '#/otra',
  ])('%s no es válida', (hash) => {
    expect(interpretar(hash)).toEqual({ vista: 'invalida' });
  });

  it('hashDe es la inversa', () => {
    expect(hashDe({ vista: 'lectura', slug: 'demo-24', capitulo: 3 })).toBe('#/novelas/demo-24/lectura/3');
    expect(hashDe({ vista: 'inicio' })).toBe('#/');
  });
});

describe('arrancar', () => {
  const fetchEspia = vi.fn<typeof fetch>();
  let raiz: HTMLElement;
  let parar: () => void;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', fetchEspia);
    fetchEspia.mockReset();
    raiz = document.createElement('div');
    document.body.replaceChildren(raiz);
  });

  afterEach(() => {
    parar?.();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    location.hash = '';
  });

  /** Vistas falsas que cuentan sus montajes y guardan las señales de sus peticiones. */
  function vistas() {
    const senales: AbortSignal[] = [];
    const montadas: string[] = [];
    const montar: Montador = (ruta) => {
      montadas.push(ruta.vista);
      const nodo = document.createElement('p');
      nodo.textContent = `vista ${ruta.vista}`;
      const vista: Vista = {
        titulo: ruta.vista,
        nodo,
        recursos: [
          {
            clave: 'recurso',
            cada: 10_000,
            pedir: (senal) => {
              senales.push(senal);
              return new Promise(() => {});
            },
          },
        ],
      };
      return vista;
    };
    return { montar, montadas, senales };
  }

  it.each([
    '#/novelas/..%2Fetc/progreso',
    '#/novelas/Demo/progreso',
    '#/novelas/demo-24/lectura/0',
    '#/novelas/demo-24/lectura/07',
    '#/novelas/demo-24/lectura/+3',
    '#/novelas/demo-24/lectura/1000',
  ])('%s: «ruta no válida», sin peticiones, sin normalizar y «sin datos» (CA-09)', async (hash) => {
    location.hash = hash;
    const { montar, montadas } = vistas();
    parar = arrancar(raiz, montar).detener;
    await vi.advanceTimersByTimeAsync(30_000);
    expect(raiz.textContent).toContain('ruta no válida');
    expect(montadas).toEqual([]);
    expect(fetchEspia).not.toHaveBeenCalled();
    expect(location.hash).toBe(hash);
    expect(raiz.querySelector('.q-api')?.textContent).toContain('sin datos');
  });

  it('cambiar de vista desmonta la anterior y aborta sus peticiones (CA-07)', async () => {
    location.hash = '#/novelas/demo-24/progreso';
    const { montar, montadas, senales } = vistas();
    parar = arrancar(raiz, montar).detener;
    await vi.advanceTimersByTimeAsync(1_000);
    location.hash = '#/novelas/demo-24/lectura';
    window.dispatchEvent(new HashChangeEvent('hashchange'));
    await vi.advanceTimersByTimeAsync(0);
    expect(montadas).toEqual(['progreso', 'lectura']);
    expect(senales[0]?.aborted).toBe(true);
    expect(raiz.textContent).toContain('vista lectura');
    expect(raiz.textContent).not.toContain('vista progreso');
  });

  it('la vista que sabe actualizarse no se vuelve a montar, y navegar refleja el capítulo en el hash (CA-10)', async () => {
    location.hash = '#/novelas/demo-24/lectura';
    const actualizadas: unknown[] = [];
    let montajes = 0;
    let abrir = (): void => {};
    parar = arrancar(raiz, (_, navegar) => {
      montajes += 1;
      abrir = () => navegar({ vista: 'lectura', slug: 'demo-24', capitulo: 3 });
      return {
        titulo: 'Lectura',
        nodo: document.createElement('div'),
        recursos: [],
        actualizar: (nueva) => actualizadas.push(nueva) > 0,
      };
    }).detener;
    abrir();
    window.dispatchEvent(new HashChangeEvent('hashchange'));
    expect(location.hash).toBe('#/novelas/demo-24/lectura/3');
    expect(actualizadas).toEqual([{ vista: 'lectura', slug: 'demo-24', capitulo: 3 }]);
    expect(montajes).toBe(1);
  });
});
