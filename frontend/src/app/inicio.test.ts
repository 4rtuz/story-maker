// CA-08 y CA-58 en su parte unitaria: una entrada por novela, vacío y error, contra el cliente
// real con fetch espiado.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { inicio } from './inicio';
import { arrancar } from './rutas';

const fetchEspia = vi.fn<typeof fetch>();
let parar: () => void;
let raiz: HTMLElement;

const cursor = (capitulo: number, fase: string, ultimo_paso: string | null) => ({
  capitulo,
  fase,
  ultimo_paso,
  intento: 1,
});

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

  it('dos novelas dan dos entradas con su cursor y sus enlaces (CA-08)', async () => {
    const novelas = [
      { slug: 'demo-24', cursor: cursor(8, 'escritura', 'aplicar-delta') },
      { slug: 'recien-creada', cursor: cursor(1, 'escritura', null) },
    ];
    fetchEspia.mockResolvedValue(new Response(JSON.stringify(novelas)));
    montar();
    await vi.advanceTimersByTimeAsync(0);
    const entradas = [...raiz.querySelectorAll('.q-entrada')];
    expect(entradas).toHaveLength(2);
    const [demo] = entradas;
    expect(demo?.textContent).toContain('demo-24');
    expect(demo?.textContent).toContain('8');
    expect(demo?.textContent).toContain('escritura');
    expect(demo?.textContent).toContain('aplicar-delta');
    const enlaces = [...(demo?.querySelectorAll('a') ?? [])].map((a) => a.getAttribute('href'));
    expect(enlaces).toContain('#/novelas/demo-24/progreso');
    expect(enlaces).toContain('#/novelas/demo-24/lectura');
    expect([...raiz.querySelectorAll('a')].map((a) => a.getAttribute('href'))).toContain('#/lanzar');
    expect(raiz.querySelector('.q-esqueleto')).toBeNull();
  });

  it('sin novelas, el texto de vacío', async () => {
    fetchEspia.mockResolvedValue(new Response('[]'));
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('todavía no hay novelas: lanza la primera');
  });

  it('con la API caída, el aviso', async () => {
    fetchEspia.mockRejectedValue(new TypeError('Failed to fetch'));
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toBe(
      'API no disponible en http://127.0.0.1:8000',
    );
  });
});
