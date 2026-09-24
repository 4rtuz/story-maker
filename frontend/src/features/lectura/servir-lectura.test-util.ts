// La API de demo-24 para los tests de Lectura: 24 capítulos en tres actos, 7 cerrados y el 8 en
// el índice. Devuelve las rutas pedidas, para afirmar lo que no se pide (CA-27).
import { vi } from 'vitest';

const NUMEROS = ['uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho'];
export const INDICE = NUMEROS.map((n, i) => ({ capitulo: i + 1, titulo: `Capítulo ${n}` }));

const rango = (desde: number, hasta: number) => Array.from({ length: hasta - desde + 1 }, (_, i) => desde + i);
export const ESCALETA = {
  actos: [
    { numero: 1, funcion_dramatica: '', capitulos: rango(1, 6) },
    { numero: 2, funcion_dramatica: '', capitulos: rango(7, 18) },
    { numero: 3, funcion_dramatica: '', capitulos: rango(19, 24) },
  ],
  puntos_de_giro: {},
  curva_tension_objetivo: [],
};

export type Respuestas = Record<string, () => Response | Promise<Response>>;
export const json = (cuerpo: unknown, status = 200) => () => new Response(JSON.stringify(cuerpo), { status });

export const COMPLETO: Respuestas = {
  '/config': json({ parametros_obra: { subgenero: 'noir', num_capitulos: 24, longitud_total_palabras: 7200 } }),
  '/escaleta': json(ESCALETA),
  '/checkpoint': json({ capitulo: 7 }),
  '/capitulos': json(INDICE),
};

/** Sirve demo-24 con `respuestas` por encima de COMPLETO; `capitulos/N` da un markdown mínimo. */
export function servirLectura(respuestas: Respuestas = {}): string[] {
  const pedidas: string[] = [];
  const espia = vi.fn<typeof fetch>((url) => {
    const ruta = String(url).replace('http://127.0.0.1:8000/novelas/demo-24', '');
    pedidas.push(ruta);
    const todas = { ...COMPLETO, ...respuestas };
    const propia = todas[ruta];
    if (propia) return Promise.resolve(propia());
    const n = ruta.match(/^\/capitulos\/(\d+)$/)?.[1];
    if (n) return Promise.resolve(new Response(`---\ncapitulo: ${n}\nrun_id: r-1\n---\n\nTexto del capítulo ${n}.\n`));
    return Promise.resolve(new Response('{"detail":"no servida"}', { status: 404 }));
  });
  vi.stubGlobal('fetch', espia);
  return pedidas;
}
