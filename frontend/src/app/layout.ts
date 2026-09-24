// El marco de todas las vistas (RF-48 a RF-50, D24, D50): barra lateral con el logo, la
// navegación, la novela de la ruta y el estado de la API; barra superior con el botón de plegar,
// el título y la hora de la última ronda correcta; y el aviso de RF-04 sobre el contenido. El
// estado de la API y la hora salen de las rondas de la vista: el layout no pide nada.
import { urlBase } from '../shared/api/cliente';
import { crearLogo } from '../shared/marca/logo';
import { icono, type NombreDeIcono } from '../shared/iconos/trazados';
import { CADA_DATOS, type Ronda } from '../shared/sondeo';
import { aviso, el } from '../shared/ui/componentes';
import type { Ruta } from './rutas';

export interface Layout {
  raiz: HTMLElement;
  /** Monta el contenido de una vista y deja la barra lateral y la superior como le tocan. */
  poner(ruta: Ruta, titulo: string, contenido: HTMLElement): void;
  informar(ronda: Ronda): void;
}

/** Texto para lectores de pantalla que sigue ahí con la barra plegada. */
const oculto = (texto: string): HTMLElement => el('span', 'q-oculto-visual', texto);

function item(texto: string, href: string, nombre: NombreDeIcono): HTMLAnchorElement {
  const a = el('a', 'q-nav__item', icono(nombre), el('span', 'q-nav__texto', texto));
  a.href = href;
  return a;
}

const hora = (d: Date): string => d.toTimeString().slice(0, 8);

export function crearLayout(): Layout {
  const navegacion = el('div', 'q-nav__bloque');
  const novela = el('div', 'q-nav__bloque');
  const estadoApi = el('span', 'q-api__estado');
  const urlApi = el('span', 'q-api__url');
  const api = el('div', 'q-api', icono('plug'), el('span', 'q-api__texto', estadoApi, urlApi));
  const barra = el('nav', 'q-nav', el('div', 'q-nav__logo', crearLogo()), navegacion, novela, api);
  barra.id = 'barra-lateral';
  barra.setAttribute('aria-label', 'Barra lateral');

  const textoPlegar = oculto('Plegar barra lateral');
  const plegar = el('button', 'q-plegar', icono('panel-left'), textoPlegar);
  plegar.type = 'button';
  plegar.setAttribute('aria-controls', barra.id);
  plegar.setAttribute('aria-expanded', 'true');
  const titulo = el('h1', 'q-barra__titulo');
  const actualizado = el('p', 'q-barra__actualizado');
  actualizado.hidden = true;
  const superior = el('header', 'q-barra', plegar, titulo, actualizado);

  const avisos = el('div', 'q-avisos');
  const contenido = el('div', 'q-contenido__vista');
  const principal = el('main', 'q-contenido', avisos, contenido);
  // El fondo oscuro va en la columna, que llega al final de la página; la barra, fija dentro.
  const raiz = el('div', 'q-app', el('div', 'q-app__lateral', barra), el('div', 'q-app__columna', superior, principal));

  plegar.addEventListener('click', () => {
    const plegada = raiz.classList.toggle('q-app--plegada');
    plegar.setAttribute('aria-expanded', String(!plegada));
    textoPlegar.textContent = plegada ? 'Desplegar barra lateral' : 'Plegar barra lateral';
  });

  function ponerApi(texto: string, url = ''): void {
    estadoApi.textContent = texto;
    urlApi.textContent = url; // vacía, guarda su línea (RNF-21)
  }

  return {
    raiz,
    poner(ruta, textoTitulo, nodo) {
      const actual = (a: HTMLAnchorElement, vista: Ruta['vista']): HTMLAnchorElement => {
        if (ruta.vista === vista) a.setAttribute('aria-current', 'page');
        return a;
      };
      navegacion.replaceChildren(
        el('p', 'q-nav__rotulo', 'Navegación'),
        actual(item('Novelas', '#/', 'library'), 'inicio'),
        actual(item('Lanzar', '#/lanzar', 'rocket'), 'lanzar'),
      );
      if ('slug' in ruta) {
        novela.replaceChildren(
          el('p', 'q-nav__rotulo q-nav__slug', ruta.slug),
          actual(item('Progreso', `#/novelas/${ruta.slug}/progreso`, 'activity'), 'progreso'),
          actual(item('Lectura', `#/novelas/${ruta.slug}/lectura`, 'book-open'), 'lectura'),
        );
      } else {
        novela.replaceChildren();
      }
      novela.hidden = !('slug' in ruta);
      titulo.textContent = textoTitulo;
      actualizado.hidden = true;
      avisos.replaceChildren();
      ponerApi('sin datos');
      contenido.replaceChildren(nodo);
    },
    informar(ronda) {
      if (ronda.cada !== CADA_DATOS) return; // la hora y el estado, de los datos de la vista
      // Un 404 o un 422 también es la API respondiendo; sin respuesta es la red o el plazo.
      const sinRespuesta = ronda.errores.some((e) => e.tipo !== 'http');
      ponerApi(sinRespuesta ? 'API sin respuesta' : 'API conectada', urlBase());
      if (ronda.correcta) {
        actualizado.textContent = `Actualizado a las ${hora(ronda.hora)}`;
        actualizado.hidden = false;
        avisos.replaceChildren();
        return;
      }
      const motivo = [...new Set(ronda.errores.map((e) => e.detalle))].join('; ');
      // El mismo aviso se deja: rehacerlo lo volvería a anunciar cada ronda.
      if (avisos.textContent !== motivo) avisos.replaceChildren(aviso(motivo));
    },
  };
}
