// CA-22 y CA-23 con el reloj simulado: el tramo de harness.log del run de run_id mayor,
// encadenado con hasta, reiniciado tras un 416, y el cambio a un run nuevo con desde=0 (D38).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { sondear, type Sondeo } from '../../shared/sondeo';
import { crearActividad, sinActividad } from './actividad';

const fetchEspia = vi.fn<typeof fetch>();
let sondeo: Sondeo | undefined;

const manifiesto = (run_id: string) => ({ run_id }) as Esquemas['Manifest'];
const MODIFICADO = '2026-09-24T10:00:00+02:00';

/** Un log en memoria servido como la API: líneas completas desde `desde` hasta el final. */
function servirLogs(logs: Record<string, string[]>, estados: Record<string, number> = {}): string[] {
  const pedidas: string[] = [];
  fetchEspia.mockImplementation((url) => {
    const u = new URL(String(url));
    const run = u.pathname.split('/')[4] ?? '';
    const desde = Number(u.searchParams.get('desde'));
    pedidas.push(`${run}?desde=${desde}`);
    const status = estados[`${run}?desde=${desde}`];
    if (status) return Promise.resolve(new Response('{"detail":"pasa del tamaño"}', { status }));
    const bytes = (logs[run] ?? []).map((l) => `${l}\n`);
    const tamano = bytes.join('').length;
    let posicion = 0;
    const lineas: string[] = [];
    for (const l of bytes) {
      if (posicion >= desde) lineas.push(l.trimEnd());
      posicion += l.length;
    }
    const cuerpo = { desde, hasta: tamano, tamano, modificado: MODIFICADO, lineas };
    return Promise.resolve(new Response(JSON.stringify(cuerpo)));
  });
  return pedidas;
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-09-24T08:05:00Z'));
  vi.stubGlobal('fetch', fetchEspia);
  fetchEspia.mockReset();
});

afterEach(() => {
  sondeo?.detener();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const LOG = Array.from({ length: 120 }, (_, i) => `2026-09-24T10:00:00+02:00 paso ${i + 1} salida=0`);

describe('actividad (CA-22)', () => {
  it('sin runs, ninguna petición y «sin runs todavía»', async () => {
    const actividad = crearActividad('demo-24');
    sondeo = sondear([actividad.recurso], () => {});
    actividad.alCambiarRuns([]);
    await vi.advanceTimersByTimeAsync(6_000);
    expect(fetchEspia).not.toHaveBeenCalled();
    expect(actividad.tarjeta.textContent).toContain('sin runs todavía');
  });

  it('encadena desde con cada hasta, y muestra las 50 últimas líneas y la hora', async () => {
    const pedidas = servirLogs({ 'r-20260924-0001': LOG });
    const actividad = crearActividad('demo-24');
    actividad.alCambiarRuns([manifiesto('r-20260924-0001')]);
    sondeo = sondear([actividad.recurso], () => {});
    await vi.advanceTimersByTimeAsync(6_000);
    const tamano = LOG.map((l) => `${l}\n`).join('').length;
    expect(pedidas).toEqual([`r-20260924-0001?desde=0`, `r-20260924-0001?desde=${tamano}`, `r-20260924-0001?desde=${tamano}`]);
    const lineas = [...actividad.tarjeta.querySelectorAll('.q-log__linea')].map((l) => l.textContent);
    expect(lineas).toHaveLength(50);
    expect(lineas.at(-1)).toContain('paso 120');
    expect(lineas[0]).toContain('paso 71');
    expect(actividad.tarjeta.textContent).toContain(new Date(MODIFICADO).toTimeString().slice(0, 8));
  });

  it('tras un 416 vuelve a desde=0 y reconstruye la lista, sin aviso', async () => {
    const tamano = LOG.map((l) => `${l}\n`).join('').length;
    const pedidas = servirLogs({ 'r-20260924-0001': LOG }, { [`r-20260924-0001?desde=${tamano}`]: 416 });
    const actividad = crearActividad('demo-24');
    actividad.alCambiarRuns([manifiesto('r-20260924-0001')]);
    const rondas: boolean[] = [];
    sondeo = sondear([actividad.recurso], (r) => rondas.push(r.correcta));
    await vi.advanceTimersByTimeAsync(6_000);
    expect(pedidas).toEqual([`r-20260924-0001?desde=0`, `r-20260924-0001?desde=${tamano}`, `r-20260924-0001?desde=0`]);
    expect(actividad.tarjeta.querySelectorAll('.q-log__linea')).toHaveLength(50);
    expect(rondas.every(Boolean)).toBe(true);
  });

  it('un run de run_id mayor se sigue desde 0 y el anterior no se pide más (VAL-13)', async () => {
    const nuevo = Array.from({ length: 3 }, (_, i) => `run nuevo, línea ${i + 1}`);
    const pedidas = servirLogs({ 'r-20260924-0001': LOG, 'r-20260924-0002': nuevo });
    const actividad = crearActividad('demo-24');
    actividad.alCambiarRuns([manifiesto('r-20260924-0001')]);
    sondeo = sondear([actividad.recurso], () => {});
    await vi.advanceTimersByTimeAsync(0);
    actividad.alCambiarRuns([manifiesto('r-20260924-0001'), manifiesto('r-20260924-0002')]);
    await vi.advanceTimersByTimeAsync(6_000);
    expect(pedidas.slice(1)).toEqual([
      'r-20260924-0002?desde=0',
      `r-20260924-0002?desde=${nuevo.map((l) => `${l}\n`).join('').length}`,
    ]);
    const lineas = [...actividad.tarjeta.querySelectorAll('.q-log__linea')].map((l) => l.textContent);
    expect(lineas).toEqual(nuevo);
  });
});

describe('sin actividad (CA-23, VAL-14)', () => {
  it('pasados 15 min desde modificado, con zona, y nunca si modificado está en el futuro', () => {
    expect(sinActividad(MODIFICADO, new Date('2026-09-24T08:15:00Z'))).toBe(false);
    expect(sinActividad(MODIFICADO, new Date('2026-09-24T08:15:01Z'))).toBe(true);
    expect(sinActividad(MODIFICADO, new Date('2026-09-24T07:55:00Z'))).toBe(false);
    expect(sinActividad(null, new Date('2026-09-24T09:00:00Z'))).toBe(false);
  });

  it('16 min muestran «sin actividad desde <hora>» y 14 min no', async () => {
    servirLogs({ 'r-20260924-0001': ['una línea'] });
    const actividad = crearActividad('demo-24');
    actividad.alCambiarRuns([manifiesto('r-20260924-0001')]);
    vi.setSystemTime(new Date('2026-09-24T08:14:00Z'));
    sondeo = sondear([actividad.recurso], () => {});
    await vi.advanceTimersByTimeAsync(0);
    expect(actividad.tarjeta.textContent).not.toContain('sin actividad desde');
    vi.setSystemTime(new Date('2026-09-24T08:16:00Z'));
    await vi.advanceTimersByTimeAsync(3_000);
    const hora = new Date(MODIFICADO).toTimeString().slice(0, 8);
    expect(actividad.tarjeta.textContent).toContain(`sin actividad desde ${hora}`);
  });
});
