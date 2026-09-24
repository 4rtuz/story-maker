// CA-05 a CA-07, RNF-05 y D45 con el reloj simulado de Vitest: nunca esperas por tiempo real.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from './api/cliente';
import { ErrorDeApi } from './api/errores';
import { sondear, type Recurso, type Ronda } from './sondeo';

let visibilidad: DocumentVisibilityState = 'visible';

beforeEach(() => {
  vi.useFakeTimers();
  visibilidad = 'visible';
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => visibilidad });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function ocultar(estado: DocumentVisibilityState): void {
  visibilidad = estado;
  document.dispatchEvent(new Event('visibilitychange'));
}

/** Un recurso que cuenta sus peticiones y guarda sus señales; tarda `ms` en responder. */
function recurso(clave: string, cada: number, ms = 0) {
  const senales: AbortSignal[] = [];
  const r: Recurso & { pedidas: number; senales: AbortSignal[] } = {
    clave,
    cada,
    pedidas: 0,
    senales,
    pedir: (senal) => {
      r.pedidas += 1;
      senales.push(senal);
      return new Promise<void>((resolver) => setTimeout(resolver, ms));
    },
  };
  return r;
}

const PROGRESO = ['estado', 'config', 'escaleta', 'checkpoint', 'capitulos', 'runs'];

describe('cadencia (CA-05)', () => {
  it('seis recursos a 10 s: en 30 s cada uno se pide 4 veces', async () => {
    const recursos = PROGRESO.map((c) => recurso(c, 10_000));
    const sondeo = sondear(recursos, () => {});
    await vi.advanceTimersByTimeAsync(30_000);
    expect(recursos.map((r) => r.pedidas)).toEqual([4, 4, 4, 4, 4, 4]);
    sondeo.detener();
  });

  it('una petición que tarda 15 s impide la del mismo recurso en t = 10 s', async () => {
    const lento = recurso('estado', 10_000, 15_000);
    const sondeo = sondear([lento, recurso('config', 10_000)], () => {});
    await vi.advanceTimersByTimeAsync(10_000);
    expect(lento.pedidas).toBe(1);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(lento.pedidas).toBe(2);
    sondeo.detener();
  });
});

describe('pestaña oculta (CA-06)', () => {
  it('60 s oculta sin peticiones; al volver, una ronda antes de 100 ms', async () => {
    const recursos = PROGRESO.map((c) => recurso(c, 10_000));
    const sondeo = sondear(recursos, () => {});
    await vi.advanceTimersByTimeAsync(1_000);
    ocultar('hidden');
    await vi.advanceTimersByTimeAsync(60_000);
    expect(recursos.map((r) => r.pedidas)).toEqual([1, 1, 1, 1, 1, 1]);
    ocultar('visible');
    await vi.advanceTimersByTimeAsync(99);
    expect(recursos.map((r) => r.pedidas)).toEqual([2, 2, 2, 2, 2, 2]);
    sondeo.detener();
  });

  it('volver con una petición en curso no la solapa (VAL-5)', async () => {
    const lento = recurso('estado', 10_000, 2_000);
    const sondeo = sondear([lento], () => {});
    await vi.advanceTimersByTimeAsync(1_000);
    ocultar('hidden');
    ocultar('visible');
    await vi.advanceTimersByTimeAsync(50);
    expect(lento.pedidas).toBe(1);
    sondeo.detener();
  });
});

describe('desmontar (CA-07)', () => {
  it('aborta las señales y no vuelve a pedir', async () => {
    const recursos = PROGRESO.map((c) => recurso(c, 10_000, 3_000));
    const sondeo = sondear(recursos, () => {});
    await vi.advanceTimersByTimeAsync(1_000);
    sondeo.detener();
    expect(recursos.flatMap((r) => r.senales).every((s) => s.aborted)).toBe(true);
    await vi.advanceTimersByTimeAsync(30_000);
    expect(recursos.map((r) => r.pedidas)).toEqual([1, 1, 1, 1, 1, 1]);
    ocultar('hidden');
    ocultar('visible');
    await vi.advanceTimersByTimeAsync(100);
    expect(recursos.map((r) => r.pedidas)).toEqual([1, 1, 1, 1, 1, 1]);
  });
});

describe('carga sobre la API (RNF-05)', () => {
  it('Progreso, con el log a 3 s, no pasa de 60 peticiones por minuto', async () => {
    const recursos = [...PROGRESO.map((c) => recurso(c, 10_000)), recurso('log', 3_000)];
    const sondeo = sondear(recursos, () => {});
    await vi.advanceTimersByTimeAsync(59_999);
    const total = recursos.reduce((n, r) => n + r.pedidas, 0);
    expect(total).toBeLessThanOrEqual(60);
    expect(total).toBe(6 * 6 + 20);
    sondeo.detener();
  });
});

describe('rondas correctas (D45)', () => {
  it('una ronda con un recurso fallido no es correcta; la siguiente en la que todos responden sí', async () => {
    let falla = true;
    const fragil: Recurso = {
      clave: 'estado',
      cada: 10_000,
      pedir: async () => {
        if (falla) throw new ErrorDeApi('http', 'no existe la novela demo-24', 404);
      },
    };
    const rondas: Ronda[] = [];
    const sondeo = sondear([fragil, recurso('config', 10_000)], (r) => rondas.push(r));
    await vi.advanceTimersByTimeAsync(0);
    falla = false;
    await vi.advanceTimersByTimeAsync(10_000);
    // El recurso de 0 ms responde 1 ms después: el reloj simulado aplaza así un setTimeout de 0
    // creado durante un tick.
    await vi.advanceTimersByTimeAsync(1);
    expect(rondas.map((r) => r.correcta)).toEqual([false, true]);
    expect(rondas[0]?.errores.map((e) => e.detalle)).toEqual(['no existe la novela demo-24']);
    sondeo.detener();
  });

  it('el 404 de la escaleta y el 416 del log no la hacen incorrecta', async () => {
    const respuestas: Record<string, Response> = {
      escaleta: new Response(JSON.stringify({ detail: 'falta' }), { status: 404 }),
      log: new Response(JSON.stringify({ detail: 'pasa' }), { status: 416 }),
    };
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => Promise.resolve(respuestas[url.includes('/log') ? 'log' : 'escaleta'])),
    );
    const rondas: Ronda[] = [];
    const sondeo = sondear(
      [
        { clave: 'escaleta', cada: 10_000, pedir: (s) => api.escaleta('demo-24', s).then(() => {}) },
        { clave: 'log', cada: 10_000, pedir: (s) => api.log('demo-24', 'r-20260107-0900', 9, s).then(() => {}) },
      ],
      (r) => rondas.push(r),
    );
    await vi.advanceTimersByTimeAsync(0);
    expect(rondas.map((r) => r.correcta)).toEqual([true]);
    sondeo.detener();
  });

  it('una ronda abortada al desmontar no se informa', async () => {
    const rondas: Ronda[] = [];
    const sondeo = sondear(
      [{ clave: 'estado', cada: 10_000, pedir: (s) => new Promise((_, no) => s.addEventListener('abort', () => no(new DOMException('', 'AbortError')))) }],
      (r) => rondas.push(r),
    );
    sondeo.detener();
    await vi.advanceTimersByTimeAsync(0);
    expect(rondas).toEqual([]);
  });

  it('la hora de la ronda es la del reloj al terminarla', async () => {
    vi.setSystemTime(new Date('2026-09-24T10:00:00'));
    const rondas: Ronda[] = [];
    const sondeo = sondear([recurso('estado', 10_000)], (r) => rondas.push(r));
    await vi.advanceTimersByTimeAsync(0);
    expect(rondas[0]?.hora.toTimeString().slice(0, 8)).toBe('10:00:00');
    sondeo.detener();
  });
});
