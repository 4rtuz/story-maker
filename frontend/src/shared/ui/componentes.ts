// Componentes del panel (spec 0004 §8.4). Se construyen con createElement y texto: ninguno inserta
// HTML, y el texto que llega del workspace entra siempre como nodo de texto (RF-26, D14).
import { icono, type NombreDeIcono } from '../iconos/trazados';

type Hijo = Node | string;

/** `document.createElement` con clase e hijos; las cadenas entran como nodos de texto. */
export function el<K extends keyof HTMLElementTagNameMap>(
  etiqueta: K,
  clase?: string,
  ...hijos: Hijo[]
): HTMLElementTagNameMap[K] {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  nodo.append(...hijos);
  return nodo;
}

export type Variante = 'primario' | 'secundario';
export type Tono = 'naranja' | 'cian';

interface OpcionesDeBoton {
  variante?: Variante;
  icono?: NombreDeIcono;
  /** «… →»: la flecha a la derecha de los botones secundarios que llevan a otra vista. */
  flecha?: boolean;
  deshabilitado?: boolean;
}

function contenidoDeBoton(texto: string, { icono: i, flecha }: OpcionesDeBoton): Hijo[] {
  const flechita = el('span', 'q-boton__flecha', '→');
  flechita.setAttribute('aria-hidden', 'true');
  return [...(i ? [icono(i)] : []), texto, ...(flecha ? [flechita] : [])];
}

export function boton(texto: string, opciones: OpcionesDeBoton = {}): HTMLButtonElement {
  const b = el('button', `q-boton q-boton--${opciones.variante ?? 'primario'}`);
  b.type = 'button';
  b.disabled = opciones.deshabilitado ?? false;
  b.append(...contenidoDeBoton(texto, opciones));
  return b;
}

/** Un enlace a otra vista con aspecto de botón: es navegación, así que es un `<a>`. */
export function enlaceBoton(texto: string, href: string, opciones: OpcionesDeBoton = {}): HTMLAnchorElement {
  const a = el('a', `q-boton q-boton--${opciones.variante ?? 'secundario'}`);
  a.href = href;
  a.append(...contenidoDeBoton(texto, opciones));
  return a;
}

export function cuadroDeIcono(nombre: NombreDeIcono, tono: Tono): HTMLElement {
  return el('span', `q-cuadro-icono q-cuadro-icono--${tono}`, icono(nombre));
}

export function chip(texto: string, clase = ''): HTMLElement {
  return el('span', `q-chip ${clase}`.trim(), texto);
}

/** El estado de una novela o un lanzamiento: un punto de color y la palabra, nunca solo color. */
export function estadoConPunto({ texto, tono }: { texto: string; tono: string }): HTMLElement {
  const punto = el('span', 'q-estado__punto');
  punto.setAttribute('aria-hidden', 'true');
  return el('span', `q-estado q-estado--${tono}`, punto, texto);
}

export interface BarraDeAvance {
  raiz: HTMLElement;
  /** `fraccion` de 0 a 1; `texto`, lo que anuncia un lector de pantalla. */
  poner(fraccion: number, texto: string): void;
}

export function barraDeAvance(nombre: string): BarraDeAvance {
  const relleno = el('span', 'q-avance__relleno');
  const raiz = el('div', 'q-avance', relleno);
  raiz.setAttribute('role', 'progressbar');
  raiz.setAttribute('aria-label', nombre);
  raiz.setAttribute('aria-valuemin', '0');
  raiz.setAttribute('aria-valuemax', '100');
  return {
    raiz,
    poner(fraccion, texto) {
      const acotada = Math.min(1, Math.max(0, fraccion));
      relleno.style.setProperty('--avance', String(acotada));
      raiz.setAttribute('aria-valuenow', String(Math.round(acotada * 100)));
      raiz.setAttribute('aria-valuetext', texto);
    },
  };
}

export interface Tarjeta {
  raiz: HTMLElement;
  cuerpo: HTMLElement;
  /** El chip de contador de la cabecera, para las tarjetas que listan elementos. */
  contar(n: number | null): void;
}

export function tarjeta({
  titulo,
  icono: nombre,
  tono = 'naranja',
  clase = '',
}: {
  titulo: string;
  icono: NombreDeIcono;
  tono?: Tono;
  clase?: string;
}): Tarjeta {
  const contador = chip('', 'q-chip--contador');
  contador.hidden = true;
  const cabecera = el(
    'header',
    'q-tarjeta__cabecera',
    cuadroDeIcono(nombre, tono),
    el('h2', 'q-tarjeta__titulo', titulo),
    contador,
  );
  const cuerpo = el('div', 'q-tarjeta__cuerpo');
  const raiz = el('section', `q-tarjeta ${clase}`.trim(), cabecera, cuerpo);
  raiz.setAttribute('aria-label', titulo);
  return {
    raiz,
    cuerpo,
    contar(n) {
      contador.hidden = n === null;
      contador.textContent = n === null ? '' : String(n);
    },
  };
}

export interface Metrica {
  raiz: HTMLElement;
  poner(valor: string, detalle?: string): void;
}

/** Tarjeta de métrica: el número grande, su etiqueta y un cuadrado de icono. */
export function metrica({ etiqueta: rotulo, icono: nombre, tono }: {
  etiqueta: string;
  icono: NombreDeIcono;
  tono: Tono;
}): Metrica {
  const valor = el('p', 'q-metrica__valor', esqueleto('q-esqueleto--metrica'));
  const detalle = el('p', 'q-metrica__detalle');
  const raiz = el(
    'section',
    'q-tarjeta q-metrica',
    cuadroDeIcono(nombre, tono),
    el('div', 'q-metrica__texto', el('h2', 'q-metrica__etiqueta', rotulo), valor, detalle),
  );
  return {
    raiz,
    poner(v, d = '') {
      valor.textContent = v;
      detalle.textContent = d; // vacío, guarda su línea: la tarjeta no crece al llegar (RNF-21)
    },
  };
}

/** Un bloque gris con las medidas finales de lo que va a llegar; oculto a los lectores. */
export function esqueleto(clase: string): HTMLElement {
  const bloque = el('div', `q-esqueleto ${clase}`);
  bloque.setAttribute('aria-hidden', 'true');
  return bloque;
}

export function vacio(texto: string): HTMLElement {
  return el('p', 'q-vacio', texto);
}

/** Un estado sin datos que ocupa su tarjeta: icono, el texto fijo, una pista y, si hay, la salida. */
export function estadoVacio({
  icono: nombre,
  texto,
  pista,
  accion,
}: {
  icono: NombreDeIcono;
  texto: string;
  pista: string;
  accion?: HTMLElement;
}): HTMLElement {
  return el(
    'div',
    'q-estado-vacio',
    cuadroDeIcono(nombre, 'naranja'),
    el('div', 'q-estado-vacio__texto', el('p', 'q-estado-vacio__titulo', texto), el('p', 'q-estado-vacio__pista', pista)),
    ...(accion ? [accion] : []),
  );
}

/** El aviso de error de RF-04: tinte naranja, icono y texto; se anuncia al aparecer. */
export function aviso(texto: string): HTMLElement {
  const nodo = el('div', 'q-aviso', icono('circle-alert'), el('p', 'q-aviso__texto', texto));
  nodo.setAttribute('role', 'alert');
  return nodo;
}

/** Tabla con cabecera; las celdas entran como texto. */
export function tabla(titulo: string, cabeceras: string[], filas: Hijo[][]): HTMLTableElement {
  const t = el('table', 'q-tabla', el('caption', 'q-tabla__titulo', titulo));
  t.append(
    el('thead', '', el('tr', '', ...cabeceras.map((c) => el('th', '', c)))),
    el('tbody', '', ...filas.map((fila) => el('tr', '', ...fila.map((celda) => el('td', '', celda))))),
  );
  for (const th of t.querySelectorAll('th')) th.scope = 'col';
  return t;
}
