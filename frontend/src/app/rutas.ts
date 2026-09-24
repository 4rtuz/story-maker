// Rutas por hash (spec 0004 §8.4, RF-09, RF-10). El slug y el capítulo se validan sobre el hash
// tal cual, sin decodificar ni normalizar, antes de montar nada: una ruta inválida no llega a
// ninguna vista y no pide nada (D41).
import { sondear, type Recurso, type Sondeo } from '../shared/sondeo';
import { el, enlaceBoton, estadoVacio } from '../shared/ui/componentes';
import { crearLayout } from './layout';

export type Ruta =
  | { vista: 'inicio' }
  | { vista: 'lanzar' }
  | { vista: 'progreso'; slug: string }
  | { vista: 'lectura'; slug: string; capitulo?: number }
  | { vista: 'invalida' };

const SLUG = /^[a-z0-9-]+$/;
const CAPITULO = /^[1-9][0-9]{0,2}$/;

export function interpretar(hash: string): Ruta {
  if (hash === '' || hash === '#' || hash === '#/') return { vista: 'inicio' };
  if (hash === '#/lanzar') return { vista: 'lanzar' };
  const [vacia, novelas, slug = '', vista, capitulo, ...resto] = hash.slice(1).split('/');
  if (vacia !== '' || novelas !== 'novelas' || !SLUG.test(slug) || resto.length) {
    return { vista: 'invalida' };
  }
  if (vista === 'progreso' && capitulo === undefined) return { vista: 'progreso', slug };
  if (vista === 'lectura' && capitulo === undefined) return { vista: 'lectura', slug };
  if (vista === 'lectura' && CAPITULO.test(capitulo ?? '')) {
    return { vista: 'lectura', slug, capitulo: Number(capitulo) };
  }
  return { vista: 'invalida' };
}

export function hashDe(ruta: Ruta): string {
  switch (ruta.vista) {
    case 'inicio':
    case 'invalida':
      return '#/';
    case 'lanzar':
      return '#/lanzar';
    case 'progreso':
      return `#/novelas/${ruta.slug}/progreso`;
    case 'lectura':
      return `#/novelas/${ruta.slug}/lectura${ruta.capitulo ? `/${ruta.capitulo}` : ''}`;
  }
}

export interface Vista {
  titulo: string;
  nodo: HTMLElement;
  recursos: Recurso[];
  /** Libera lo que no sea DOM, como la escena de Three.js (RF-31). */
  desmontar?(): void;
  /** Para un cambio dentro de la misma vista, como abrir un capítulo: true si lo atiende. */
  actualizar?(ruta: Ruta): boolean;
}

export type Montador = (ruta: Exclude<Ruta, { vista: 'invalida' }>, navegar: (ruta: Ruta) => void) => Vista;

const mismaVista = (a: Ruta, b: Ruta): boolean =>
  a.vista === b.vista && ('slug' in a ? a.slug : '') === ('slug' in b ? b.slug : '');

export function arrancar(raiz: HTMLElement, montar: Montador): { detener(): void } {
  const layout = crearLayout();
  raiz.replaceChildren(layout.raiz);
  let actual: { hash: string; ruta: Ruta; vista?: Vista; sondeo?: Sondeo } | undefined;

  const navegar = (ruta: Ruta): void => {
    location.hash = hashDe(ruta);
    mostrar();
  };

  function mostrar(): void {
    const hash = location.hash;
    if (actual?.hash === hash) return;
    const ruta = interpretar(hash);
    if (actual?.vista?.actualizar && mismaVista(actual.ruta, ruta) && actual.vista.actualizar(ruta)) {
      actual = { ...actual, hash, ruta };
      return;
    }
    actual?.sondeo?.detener();
    actual?.vista?.desmontar?.();
    if (ruta.vista === 'invalida') {
      const salida = enlaceBoton('Ver las novelas', '#/', { flecha: true });
      const aviso = estadoVacio({
        icono: 'circle-alert',
        texto: 'ruta no válida',
        pista: 'La dirección no corresponde a ninguna vista del panel; no se ha pedido nada a la API.',
        accion: salida,
      });
      layout.poner(ruta, 'Ruta no válida', el('section', 'q-tarjeta', aviso));
      actual = { hash, ruta };
      return;
    }
    const vista = montar(ruta, navegar);
    layout.poner(ruta, vista.titulo, vista.nodo);
    actual = { hash, ruta, vista, sondeo: sondear(vista.recursos, (r) => layout.informar(r)) };
  }

  window.addEventListener('hashchange', mostrar);
  mostrar();
  return {
    detener() {
      window.removeEventListener('hashchange', mostrar);
      actual?.sondeo?.detener();
      actual?.vista?.desmontar?.();
    },
  };
}
