// Progreso contra el cliente real con fetch espiado (spec 0015): cifras, proceso de creación con
// sus animaciones de cambio, métricas de Langfuse y tensión; sin hilos, runs ni actividad. Y el
// error con los datos anteriores conservados (CA-04, CA-58 en su parte unitaria).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { arrancar } from '../../app/rutas';
import { progreso } from './vista';

const fetchEspia = vi.fn<typeof fetch>();
let parar: () => void;
let raiz: HTMLElement;

const estado = (fase = 'escritura') => ({
  cursor: { capitulo: 8, fase, ultimo_paso: 'briefing', intento: 1 },
  metricas: { palabras_totales: 21000, desviacion_vs_plan: 0 },
  hilos: [{ id: 'hil-001', estado: 'abierto', abierto_en: 1, cerrado_en: null, descripcion: 'La carta sin remitente' }],
  tension_real: [4, 5],
});
const CONFIG = { parametros_obra: { subgenero: 'noir', num_capitulos: 24, longitud_total_palabras: 72000 } };
const consumo = (coste: number) => ({
  llamadas: 12,
  tokens_entrada: 1000,
  tokens_salida: 100,
  tokens_cache_lectura: 500,
  coste_usd: coste,
  latencia_media_llamada_s: 3,
});
const METRICAS = {
  slug: 'demo-24',
  sesion: 'novela-demo-24',
  generado: '2026-09-25T10:00:00Z',
  pasos: [{ paso: 'capitulo 01', ...consumo(2.5), latencia_s: 840, roles: { escritor: consumo(2), cronista: consumo(0.5) } }],
  total: { ...consumo(2.5), latencia_s: 840 },
};

type Respuestas = Record<string, () => Response | Promise<Response>>;

function servir(respuestas: Respuestas): void {
  fetchEspia.mockImplementation((url) => {
    const ruta = String(url).replace('http://127.0.0.1:8000', '');
    return Promise.resolve(respuestas[ruta]?.() ?? new Response('null'));
  });
}

const json = (cuerpo: unknown, status = 200) => () => new Response(JSON.stringify(cuerpo), { status });
const N = '/novelas/demo-24';
const completo: Respuestas = {
  [`${N}/estado`]: json(estado()),
  [`${N}/config`]: json(CONFIG),
  [`${N}/checkpoint`]: json({ capitulo: 7 }),
  [`${N}/escaleta`]: json({ detail: 'falta' }, 404),
  [`${N}/libro`]: json({ titulo: 'El faro apagado', dedicatoria: null, capitulos: [], personajes: [], lugares: [] }),
  [`${N}/metricas`]: json(METRICAS),
  ['/lanzamientos']: json([{ slug: 'demo-24', estado: 'en_marcha', paso: 'capitulo 08', detalle: '', actualizado: '2026-09-25T10:00:00Z' }]),
};
const conEscaleta = { ...completo, [`${N}/escaleta`]: json({ actos: [], curva_tension_objetivo: [], puntos_de_giro: { detonante: 2, punto_medio: 12, crisis: 18, climax: 22, resolucion: 24 } }) };

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
  it('esqueleto mientras llegan los datos, con el slug como título provisional', () => {
    fetchEspia.mockReturnValue(new Promise(() => {}));
    montar();
    expect(raiz.querySelector('.q-ficha__titulo')?.textContent).toBe('Demo 24');
    expect(raiz.querySelectorAll('.q-esqueleto').length).toBeGreaterThanOrEqual(4);
  });

  it('con datos: título, cifras, métricas de Langfuse y tensión; sin hilos, runs ni actividad', async () => {
    servir(conEscaleta);
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('.q-ficha__titulo')?.textContent).toBe('El faro apagado');
    expect(raiz.textContent).toContain('de 24 capítulos');
    expect(raiz.textContent).toContain('21.000');
    expect(raiz.textContent).toContain('14 min');
    expect(raiz.textContent).toContain('Escritor');
    expect(raiz.querySelectorAll('.q-barras__col')).toHaveLength(1);
    expect(raiz.textContent).not.toMatch(/Hilos abiertos|Runs|Actividad|La carta sin remitente/);
    expect(raiz.querySelector('.q-esqueleto')).toBeNull();
  });

  it('el proceso de creación gira en el hito en curso y marca el que termina', async () => {
    servir(conEscaleta);
    montar();
    await vi.advanceTimersByTimeAsync(0);
    const actual = raiz.querySelector('.q-hito[aria-current="step"]');
    expect(actual?.textContent).toBe('Escribiendo el capítulo 8');
    expect(actual?.querySelector('.q-girando')).not.toBeNull();
    expect(raiz.querySelector('.q-hito--recien')).toBeNull(); // al entrar, nada se anima
    servir({ ...conEscaleta, [`${N}/estado`]: json(estado('revision')) });
    await vi.advanceTimersByTimeAsync(10_000);
    const recien = raiz.querySelector('.q-hito--recien');
    expect(recien?.textContent).toBe('Capítulo 8 escrito');
    expect(recien?.querySelector('.q-marca')).not.toBeNull();
    expect(raiz.querySelector('.q-hito[aria-current="step"]')?.textContent).toBe('Evaluando el capítulo 8');
    expect(raiz.querySelector('[role="progressbar"][aria-label="Avance de la novela"]')?.getAttribute('aria-valuenow')).toBe('31');
  });

  it('sin métricas guardadas, lo dice sin aviso de error', async () => {
    servir({ ...completo, [`${N}/metricas`]: json({ detail: 'no' }, 404) });
    montar();
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.textContent).toContain('Todavía no hay métricas de Langfuse');
    expect(raiz.querySelector('[role="alert"]')).toBeNull();
    // CA-19: sin escaleta, la serie real y su texto, sin aviso de error.
    expect(raiz.textContent).toContain('el plan todavía no tiene escaleta');
  });

  it('un 404 en estado da el aviso y conserva lo anterior (CA-04)', async () => {
    servir(conEscaleta);
    montar();
    await vi.advanceTimersByTimeAsync(0);
    servir({ ...conEscaleta, [`${N}/estado`]: json({ detail: 'no existe la novela demo-24' }, 404) });
    await vi.advanceTimersByTimeAsync(10_000);
    await vi.advanceTimersByTimeAsync(1);
    expect(raiz.querySelector('[role="alert"]')?.textContent).toBe('no existe la novela demo-24');
    expect(raiz.textContent).toContain('21.000');
    expect(raiz.querySelector('.q-hito[aria-current="step"]')?.textContent).toBe('Escribiendo el capítulo 8');
  });
});
