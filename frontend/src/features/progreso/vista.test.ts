// La cáscara de Progreso contra el cliente real con fetch espiado: esqueleto, vacío, error con los
// datos anteriores conservados (CA-04 y CA-58 en su parte unitaria).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { arrancar } from '../../app/rutas';
import { progreso } from './vista';

const fetchEspia = vi.fn<typeof fetch>();
let parar: () => void;
let raiz: HTMLElement;

const hilo = { id: 'hil-001', estado: 'abierto', abierto_en: 1, cerrado_en: null, descripcion: 'La carta sin remitente' };
const ESTADO = {
  cursor: { capitulo: 8, fase: 'escritura', ultimo_paso: 'briefing', intento: 1 },
  metricas: { palabras_totales: 2100, desviacion_vs_plan: 0 },
  hilos: [hilo],
  tension_real: [4, 5],
};
const CONFIG = { parametros_obra: { subgenero: 'noir', num_capitulos: 24, longitud_total_palabras: 7200 } };

type Respuestas = Record<string, () => Response | Promise<Response>>;

function servir(respuestas: Respuestas): void {
  fetchEspia.mockImplementation((url) => {
    const ruta = String(url).replace('http://127.0.0.1:8000/novelas/demo-24', '');
    const clave = Object.keys(respuestas).find((k) => ruta === k || ruta.startsWith(`${k}?`));
    return Promise.resolve(clave ? respuestas[clave]!() : new Response('null'));
  });
}

const json = (cuerpo: unknown, status = 200) => () => new Response(JSON.stringify(cuerpo), { status });
const completo: Respuestas = {
  '/estado': json(ESTADO),
  '/config': json(CONFIG),
  '/checkpoint': json({ capitulo: 7 }),
  '/capitulos': json([]),
  '/runs': json([]),
  '/escaleta': json({ detail: 'falta' }, 404),
};

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', fetchEspia);
  fetchEspia.mockReset();
  location.hash = '#/novelas/demo-24/progreso';
  raiz = document.createElement('div');
  document.body.replaceChildren(raiz);
});

afterEach(() => {
  parar?.();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function montar(): void {
  parar = arrancar(raiz, (ruta) => progreso(ruta as { vista: 'progreso'; slug: string })).detener;
}

describe('Progreso', () => {
  it('esqueleto mientras llegan los datos', () => {
    fetchEspia.mockReturnValue(new Promise(() => {}));
    montar();
    expect(raiz.querySelector('.q-banner__titular')?.textContent).toBe('demo-24');
    expect(raiz.querySelectorAll('.q-esqueleto').length).toBeGreaterThanOrEqual(4);
  });

  it('con datos: métricas, banner, hilos y sin runs', async () => {
    servir(completo);
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('cerrados: 7 de 24');
    expect(raiz.textContent).toContain('NOIR · 24 CAPÍTULOS');
    expect(raiz.textContent).toContain('La carta sin remitente');
    expect(raiz.textContent).toContain('sin runs todavía');
    expect(raiz.querySelector('.q-esqueleto')).toBeNull();
  });

  it('sin hilos abiertos, su texto de vacío', async () => {
    servir({ ...completo, '/estado': json({ ...ESTADO, hilos: [] }) });
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('no hay hilos abiertos');
  });

  it('un 404 en estado da el aviso y conserva el cursor anterior (CA-04)', async () => {
    servir(completo);
    montar();
    await vi.advanceTimersByTimeAsync(0);
    servir({ ...completo, '/estado': json({ detail: 'no existe la novela demo-24' }, 404) });
    await vi.advanceTimersByTimeAsync(10_000);
    await vi.advanceTimersByTimeAsync(1);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toBe('no existe la novela demo-24');
    expect(raiz.textContent).toContain('Fase: escritura');
    expect(raiz.textContent).toContain('cerrados: 7 de 24');
  });
});
