// CA-08 y CA-58 en su parte unitaria, con la biblioteca de la spec 0015 (RF-08): una portada por
// novela visible, con su título, su estado y sus enlaces; vacío y error.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { inicio } from './inicio';
import { arrancar } from './rutas';

const fetchEspia = vi.fn<typeof fetch>();
let parar: () => void;
let raiz: HTMLElement;

const cursor = { capitulo: 3, fase: 'escritura', ultimo_paso: null, intento: 1 };
const respuesta = (cuerpo: unknown, status = 200) => new Response(JSON.stringify(cuerpo), { status });
const config = (num_capitulos: number) => ({
  idea_semilla: 'x',
  parametros_obra: { num_capitulos, subgenero: 'noir', longitud_total_palabras: 1000, palabras_por_capitulo: { min: 1, objetivo: 2, max: 3 } },
  parametros_sistema: {},
});
const libro = (titulo: string, cerrados: number) => ({
  titulo,
  dedicatoria: null,
  capitulos: Array.from({ length: cerrados }, (_, i) => ({ capitulo: i + 1, titulo: `C${i + 1}` })),
  personajes: [],
  lugares: [],
});

function api(rutas: Record<string, () => Response>) {
  fetchEspia.mockImplementation((url) => {
    const clave = String(url).replace('http://127.0.0.1:8000', '');
    return Promise.resolve(rutas[clave]?.() ?? respuesta({ detail: 'no' }, 404));
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', fetchEspia);
  fetchEspia.mockReset();
  location.hash = '#/';
  raiz = document.createElement('div');
  document.body.replaceChildren(raiz);
});

afterEach(() => {
  parar?.();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function montar(): void {
  parar = arrancar(raiz, () => inicio()).detener;
}

describe('Inicio', () => {
  it('muestra el esqueleto mientras llega la primera respuesta', () => {
    fetchEspia.mockReturnValue(new Promise(() => {}));
    montar();
    expect(raiz.querySelectorAll('.q-esqueleto').length).toBeGreaterThan(0);
  });

  it('una portada por novela visible, con su título, su estado y sus enlaces (CA-08, RF-08)', async () => {
    const slugs = ['demo-24', 'eval-b2-nino', 'humo-0003', 'regalo-carmen', 'faro'];
    api({
      '/novelas': () => respuesta(slugs.map((slug) => ({ slug, cursor }))),
      '/lanzamientos': () => respuesta([{ slug: 'faro', estado: 'en_marcha', paso: 'capitulo 02', detalle: '', actualizado: '2026-09-25T10:00:00Z' }]),
      '/novelas/demo-24/libro': () => respuesta(libro('El faro apagado', 10)),
      '/novelas/demo-24/config': () => respuesta(config(10)),
      '/novelas/faro/libro': () => respuesta(libro('Mareas', 1)),
      '/novelas/faro/config': () => respuesta(config(8)),
    });
    montar();
    await vi.advanceTimersByTimeAsync(0);
    const obras = [...raiz.querySelectorAll('.q-obra:not(.q-obra--nueva)')];
    expect(obras.map((o) => o.getAttribute('data-slug'))).toEqual(['demo-24', 'faro']);
    const [demo, faro] = obras;
    expect(demo?.textContent).toContain('El faro apagado');
    expect(demo?.textContent).toContain('Terminada');
    expect(faro?.textContent).toContain('Escribiéndose');
    expect(faro?.textContent).toContain('1 de 8 capítulos');
    expect(demo?.querySelector('img')?.getAttribute('src')).toBe('http://127.0.0.1:8000/novelas/demo-24/portada');
    const enlaces = [...(demo?.querySelectorAll('a') ?? [])].map((a) => a.getAttribute('href'));
    expect(enlaces).toContain('#/novelas/demo-24/progreso');
    expect(enlaces).toContain('#/novelas/demo-24/lectura');
    expect([...raiz.querySelectorAll('a')].map((a) => a.getAttribute('href'))).toContain('#/lanzar');
    expect(raiz.querySelector('.q-esqueleto')).toBeNull();
  });

  it('sin libro todavía, el slug hace de título', async () => {
    api({ '/novelas': () => respuesta([{ slug: 'recien-creada', cursor }]), '/lanzamientos': () => respuesta([]) });
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('.q-obra[data-slug]')?.textContent).toContain('Recien creada');
  });

  it('sin novelas, el texto de vacío', async () => {
    api({ '/novelas': () => respuesta([]), '/lanzamientos': () => respuesta([]) });
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('todavía no hay novelas: lanza la primera');
  });

  it('con la API caída, el aviso', async () => {
    fetchEspia.mockRejectedValue(new TypeError('Failed to fetch'));
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toBe('API no disponible en http://127.0.0.1:8000');
  });
});
