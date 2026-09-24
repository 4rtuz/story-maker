// La tensión real frente a la objetivo (RF-18, RF-19, RF-55; D46). La serie es una función pura;
// el SVG se dibuja con createElementNS y con los colores de los roles que da el lector de tokens:
// ningún color propio.
import type { Esquemas } from '../../shared/api/cliente';
import { hex, type LectorDeTokens } from '../../shared/marca/lector-de-tokens';

export interface Punto {
  capitulo: number;
  valor: number;
}

export interface SerieDeTension {
  /** El eje x: hasta el mayor de los dos tamaños (D46). */
  capitulos: number;
  objetivo: number[];
  real: (number | null)[];
  /** La serie real, partida en cada null: sin interpolar. */
  tramos: Punto[][];
  sinPuntuar: number[];
  bandas: { acto: number; desde: number; hasta: number }[];
  giros: { nombre: string; capitulo: number }[];
  hayReal: boolean;
  hayEscaleta: boolean;
}

const GIROS = {
  detonante: 'Detonante',
  punto_medio: 'Punto medio',
  crisis: 'Crisis',
  climax: 'Clímax',
  resolucion: 'Resolución',
} as const satisfies Record<keyof Esquemas['PuntosDeGiro'], string>;

export function serieDeTension(real: (number | null)[], escaleta: Esquemas['Escaleta'] | null): SerieDeTension {
  const tramos: Punto[][] = [[]];
  real.forEach((valor, i) => {
    if (valor === null) tramos.push([]);
    else tramos.at(-1)?.push({ capitulo: i + 1, valor });
  });
  const objetivo = escaleta?.curva_tension_objetivo ?? [];
  return {
    capitulos: Math.max(real.length, objetivo.length),
    objetivo,
    real,
    tramos: tramos.filter((t) => t.length),
    sinPuntuar: real.flatMap((v, i) => (v === null ? [i + 1] : [])),
    bandas: (escaleta?.actos ?? []).map((a) => ({
      acto: a.numero,
      desde: Math.min(...a.capitulos),
      hasta: Math.max(...a.capitulos),
    })),
    giros: escaleta
      ? Object.entries(GIROS).map(([clave, nombre]) => ({
          nombre,
          capitulo: escaleta.puntos_de_giro[clave as keyof typeof GIROS],
        }))
      : [],
    hayReal: real.some((v) => v !== null),
    hayEscaleta: escaleta !== null,
  };
}

/** La tabla equivalente: capítulo, objetivo y real, con «sin puntuar» en un null y «—» sin valor. */
export function filasDeTension(serie: SerieDeTension): [string, string, string][] {
  return Array.from({ length: serie.capitulos }, (_, i) => {
    const real = serie.real[i];
    const objetivo = serie.objetivo[i];
    return [
      String(i + 1),
      objetivo === undefined ? '—' : String(objetivo),
      real === undefined ? '—' : real === null ? 'sin puntuar' : String(real),
    ];
  });
}

const SVG = 'http://www.w3.org/2000/svg';
// El ancho de media rejilla a 1440 px: el texto del SVG se ve a su tamaño, sin escalar.
const [ANCHO, ALTO] = [470, 250];
const [IZQ, DER, ARR, ABA] = [30, 8, 26, 30];
const LETRA = 12;

function nodo<K extends keyof SVGElementTagNameMap>(
  etiqueta: K,
  atributos: Record<string, string | number>,
  texto?: string,
): SVGElementTagNameMap[K] {
  const n = document.createElementNS(SVG, etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) n.setAttribute(clave, String(valor));
  if (texto !== undefined) n.textContent = texto;
  return n;
}

export function graficaDeTension(serie: SerieDeTension, leer: LectorDeTokens): SVGSVGElement {
  const color = (rol: string): string => hex(leer(rol));
  const n = Math.max(serie.capitulos, 1);
  const paso = (ANCHO - IZQ - DER) / n;
  const x = (capitulo: number): number => IZQ + (capitulo - 0.5) * paso;
  const y = (valor: number): number => ARR + ((10 - valor) / 9) * (ALTO - ARR - ABA);
  const linea = (puntos: Punto[]): string => puntos.map((p) => `${x(p.capitulo)},${y(p.valor)}`).join(' ');

  const svg = nodo('svg', {
    class: 'q-tension',
    viewBox: `0 0 ${ANCHO} ${ALTO}`,
    role: 'img',
    'aria-label': 'Tensión real y objetivo por capítulo; los datos están en la tabla',
  });
  for (const b of serie.bandas) {
    const [x0, x1] = [IZQ + (b.desde - 1) * paso, IZQ + b.hasta * paso];
    svg.append(
      nodo('rect', { class: 'q-tension__banda', x: x0 + 1, y: ARR, width: x1 - x0 - 2, height: ALTO - ARR - ABA, fill: color('--q-secundario-fondo'), rx: 4 }),
      // Dentro del marco aunque el acto sea estrecho y esté al final.
      nodo('text', { x: Math.min(x0 + 4, ANCHO - DER - 40), y: ARR - 9, fill: color('--q-texto'), 'font-size': LETRA }, `Acto ${b.acto}`),
    );
  }
  for (const v of [1, 5, 10]) {
    svg.append(nodo('text', { x: IZQ - 8, y: y(v) + 4, 'text-anchor': 'end', fill: color('--q-texto-secundario'), 'font-size': LETRA }, String(v)));
  }
  for (const g of serie.giros) {
    const title = nodo('title', {}, `${g.nombre}: capítulo ${g.capitulo}`);
    const marca = nodo('line', { class: 'q-tension__giro', x1: x(g.capitulo), x2: x(g.capitulo), y1: ARR, y2: ALTO - ABA, stroke: color('--q-texto-secundario'), 'stroke-width': 1, 'stroke-dasharray': '2 3' });
    marca.append(title);
    svg.append(marca);
  }
  if (serie.objetivo.length) {
    const puntos = serie.objetivo.map((valor, i) => ({ capitulo: i + 1, valor }));
    svg.append(nodo('polyline', { class: 'q-tension__objetivo', points: linea(puntos), fill: 'none', stroke: color('--q-icono-cian'), 'stroke-width': 2, 'stroke-dasharray': '6 5' }));
  }
  for (const tramo of serie.tramos) {
    svg.append(nodo('polyline', { class: 'q-tension__real', points: linea(tramo), fill: 'none', stroke: color('--q-primario'), 'stroke-width': 2.5, 'stroke-linejoin': 'round' }));
    // Un punto por valor: un tramo de un solo capítulo tampoco desaparece (VAL-11).
    for (const p of tramo) {
      svg.append(nodo('circle', { class: 'q-tension__punto', cx: x(p.capitulo), cy: y(p.valor), r: 3.5, fill: color('--q-primario') }));
    }
  }
  const eje = Math.max(1, Math.ceil(n / 12));
  for (let c = 1; c <= n; c += eje) {
    svg.append(nodo('text', { x: x(c), y: ALTO - 10, 'text-anchor': 'middle', fill: color('--q-texto-secundario'), 'font-size': LETRA }, String(c)));
  }
  return svg;
}
