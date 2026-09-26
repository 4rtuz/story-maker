// Trazados de los iconos del panel (spec 0004 §8.4 y spec 0015), copiados sin cambios de los SVG de
// lucide-static 1.48.0 (licencia ISC, en LICENSE junto a este fichero). La fuente display es de
// @fontsource/outfit 5.3.0 (OFL, en shared/marca/fuentes/OFL.txt). Se dibujan con createElementNS:
// ni CDN ni paquete npm (RF-56, D25).

type Elemento = readonly [etiqueta: 'path' | 'circle' | 'line' | 'rect', atributos: Record<string, string>];

const TRAZADOS = {
  'activity': [['path',{'d':'M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2'}]],
  'book-open': [['path',{'d':'M12 5v16'}],['path',{'d':'M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z'}]],
  'chart-line': [['path',{'d':'M3 3v16a2 2 0 0 0 2 2h16'}],['path',{'d':'m19 9-5 5-4-4-3 3'}]],
  'circle-alert': [['circle',{'cx':'12','cy':'12','r':'10'}],['line',{'x1':'12','x2':'12','y1':'8','y2':'12'}],['line',{'x1':'12','x2':'12.01','y1':'16','y2':'16'}]],
  'library': [['path',{'d':'m16 6 4 14'}],['path',{'d':'M12 6v14'}],['path',{'d':'M8 8v12'}],['path',{'d':'M4 4v16'}]],
  'panel-left': [['rect',{'width':'18','height':'18','x':'3','y':'3','rx':'2'}],['path',{'d':'M9 3v18'}]],
  'plug': [['path',{'d':'M12 22v-5'}],['path',{'d':'M15 8V2'}],['path',{'d':'M17 8a1 1 0 0 1 1 1v4a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1z'}],['path',{'d':'M9 8V2'}]],
  'rocket': [['path',{'d':'M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5'}],['path',{'d':'M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09'}],['path',{'d':'M9 12a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.4 22.4 0 0 1-4 2z'}],['path',{'d':'M9 12H4s.55-3.03 2-4c1.62-1.08 5 .05 5 .05'}]],
  'circle-dollar-sign': [['circle',{'cx':'12','cy':'12','r':'10'}],['path',{'d':'M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8'}],['path',{'d':'M12 18V6'}]],
  'download': [['path',{'d':'M12 15V3'}],['path',{'d':'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'}],['path',{'d':'m7 10 5 5 5-5'}]],
  'clock': [['circle',{'cx':'12','cy':'12','r':'10'}],['path',{'d':'M12 6v6l4 2'}]],
  'pause': [['rect',{'x':'14','y':'3','width':'5','height':'18','rx':'1'}],['rect',{'x':'5','y':'3','width':'5','height':'18','rx':'1'}]],
  'rotate-ccw': [['path',{'d':'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'}],['path',{'d':'M3 3v5h5'}]],
  'send': [['path',{'d':'M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z'}],['path',{'d':'m21.854 2.147-10.94 10.939'}]],
  'sparkles': [['path',{'d':'M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z'}],['path',{'d':'M20 2v4'}],['path',{'d':'M22 4h-4'}],['circle',{'cx':'4','cy':'20','r':'2'}]],
} as const satisfies Record<string, readonly Elemento[]>;

export type NombreDeIcono = keyof typeof TRAZADOS;
export const NOMBRES_DE_ICONO = Object.keys(TRAZADOS) as NombreDeIcono[];

const SVG = 'http://www.w3.org/2000/svg';

/** El icono como `<svg>` en `currentColor`, oculto a los lectores de pantalla: siempre va junto a
 * un texto o dentro de un control con nombre accesible. Tamaño y trazo, en estilos.css. */
export function icono(nombre: NombreDeIcono): SVGSVGElement {
  const svg = document.createElementNS(SVG, 'svg');
  const atributos = {
    class: 'q-icono',
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'aria-hidden': 'true',
    focusable: 'false',
  };
  for (const [clave, valor] of Object.entries(atributos)) svg.setAttribute(clave, valor);
  for (const [etiqueta, propios] of TRAZADOS[nombre] as readonly Elemento[]) {
    const hijo = document.createElementNS(SVG, etiqueta);
    for (const [clave, valor] of Object.entries(propios)) hijo.setAttribute(clave, valor);
    svg.append(hijo);
  }
  return svg;
}
