// «Proceso de creación» (spec 0015, RF-11): la barra de avance y los últimos hitos. El hito en
// curso lleva un indicador de carga; el que acaba de terminar dibuja su marca una vez. Solo se
// anima lo que cambia entre dos rondas: al entrar en la vista, lo hecho ya está hecho.
import { barraDeAvance, el } from '../../shared/ui/componentes';
import type { Hito, Proceso } from './proceso';

const VISIBLES = 7;
const SVG = 'http://www.w3.org/2000/svg';

function marca(): SVGSVGElement {
  const svg = document.createElementNS(SVG, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', 'q-marca');
  svg.setAttribute('aria-hidden', 'true');
  const circulo = document.createElementNS(SVG, 'circle');
  for (const [k, v] of Object.entries({ cx: '12', cy: '12', r: '10', class: 'q-marca__circulo', pathLength: '1' })) circulo.setAttribute(k, v);
  const trazo = document.createElementNS(SVG, 'path');
  for (const [k, v] of Object.entries({ d: 'M7.5 12.5l3 3 6-6.5', class: 'q-marca__trazo', pathLength: '1' })) trazo.setAttribute(k, v);
  svg.append(circulo, trazo);
  return svg;
}

function indicador(estado: Hito['estado']): Element {
  if (estado === 'hecho') return marca();
  const nodo = el('span', estado === 'en-curso' ? 'q-girando' : 'q-hito__quieto');
  nodo.setAttribute('aria-hidden', 'true');
  return nodo;
}

export interface Creacion {
  raiz: HTMLElement;
  poner(p: Proceso, contexto: string): void;
}

export function crearCreacion(): Creacion {
  const avance = barraDeAvance('Avance de la novela');
  const porcentaje = el('p', 'q-creacion__porcentaje');
  const contexto = el('p', 'q-creacion__contexto');
  const lista = el('ol', 'q-hitos');
  const raiz = el(
    'div',
    'q-creacion',
    el('div', 'q-creacion__cifras', porcentaje, contexto),
    avance.raiz,
    lista,
  );
  let vistos: Map<string, Hito['estado']> | null = null;

  return {
    raiz,
    poner(p, textoContexto) {
      porcentaje.textContent = `${p.porcentaje} %`;
      contexto.textContent = textoContexto;
      avance.poner(p.porcentaje / 100, `${p.porcentaje} %, ${textoContexto}`);
      const anteriores = vistos;
      const firma = (h: Hito): string => `${h.clave}|${h.estado}|${h.texto}`;
      const actuales = p.hitos.slice(-VISIBLES);
      if (anteriores && lista.dataset.firma === actuales.map(firma).join(';')) return; // nada nuevo: no se reinicia ninguna animación
      lista.dataset.firma = actuales.map(firma).join(';');
      lista.replaceChildren(
        ...actuales.map((h) => {
          const antes = anteriores?.get(h.clave);
          const clases = ['q-hito', `q-hito--${h.estado}`];
          if (anteriores && h.estado === 'hecho' && antes !== 'hecho') clases.push('q-hito--recien');
          if (anteriores && antes === undefined) clases.push('q-hito--entra');
          const li = el('li', clases.join(' '), indicador(h.estado), el('span', 'q-hito__texto', h.texto));
          li.dataset.clave = h.clave;
          if (h.estado === 'en-curso') li.setAttribute('aria-current', 'step');
          return li;
        }),
      );
      vistos = new Map(p.hitos.map((h) => [h.clave, h.estado]));
    },
  };
}
