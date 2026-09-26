// Inicio (RF-08, spec 0015 RF-08): la biblioteca. Una portada por novela visible con su título, su
// estado y su avance, y una tarjeta para escribir una nueva. Cada tarjeta se crea una vez y se
// actualiza en cada ronda, para no volver a pedir su imagen.
import * as api from '../shared/api/cliente';
import { icono } from '../shared/iconos/trazados';
import { estadoDeObra, SUBGENEROS } from '../shared/obra';
import { CADA_DATOS } from '../shared/sondeo';
import { barraDeAvance, el, esqueleto, estadoConPunto, estadoVacio } from '../shared/ui/componentes';
import { portada, tituloDe } from '../shared/ui/portada';
import { esVisible } from '../shared/visibles';
import type { Vista } from './rutas';

type E = api.Esquemas;

interface Ficha {
  slug: string;
  libro: E['Libro'] | null;
  config: E['Config'] | null;
  lanzamiento: E['Lanzamiento'] | undefined;
}

const valor = <T>(r: PromiseSettledResult<T>): T | null => (r.status === 'fulfilled' ? r.value : null);

function enlace(texto: string, href: string): HTMLAnchorElement {
  const a = el('a', 'q-obra__enlace', texto);
  a.href = href;
  return a;
}

function crearObra(slug: string): { raiz: HTMLElement; poner(f: Ficha): void } {
  const cubierta = portada({ slug });
  const abrir = el('a', 'q-obra__cubierta', cubierta.raiz);
  abrir.href = `#/novelas/${slug}/lectura`;
  const estado = el('p', 'q-obra__estado');
  const avance = barraDeAvance('Capítulos cerrados');
  const meta = el('p', 'q-obra__meta');
  const raiz = el(
    'article',
    'q-obra',
    abrir,
    el(
      'div',
      'q-obra__pie',
      estado,
      avance.raiz,
      meta,
      el('p', 'q-obra__enlaces', enlace('Leer', `#/novelas/${slug}/lectura`), enlace('Progreso', `#/novelas/${slug}/progreso`)),
    ),
  );
  raiz.dataset.slug = slug;
  return {
    raiz,
    poner({ libro, config, lanzamiento }) {
      const obra = config?.parametros_obra;
      const total = obra?.num_capitulos ?? 0;
      const cerrados = libro?.capitulos.length ?? 0;
      cubierta.poner(tituloDe(libro, slug), obra ? SUBGENEROS[obra.subgenero] : '');
      estado.replaceChildren(estadoConPunto(estadoDeObra(cerrados, total, lanzamiento)));
      avance.poner(total ? cerrados / total : 0, `${cerrados} de ${total} capítulos`);
      meta.textContent = total ? `${cerrados} de ${total} capítulos` : 'Preparando la biblia';
    },
  };
}

function tarjetaNueva(): HTMLElement {
  const a = el(
    'a',
    'q-obra q-obra--nueva',
    el('span', 'q-obra__chispa', icono('sparkles')),
    el('span', 'q-obra__nueva-titulo', 'Escribir una novela'),
    el('span', 'q-obra__nueva-texto', 'Cuéntame la idea y me pongo con ella.'),
  );
  a.href = '#/lanzar';
  return a;
}

export function inicio(): Vista {
  const obras = new Map<string, ReturnType<typeof crearObra>>();
  const nueva = tarjetaNueva();
  const estanteria = el('div', 'q-estanteria', nueva, ...[0, 1, 2].map(() => esqueleto('q-esqueleto--obra')));
  const cuenta = el('p', 'q-biblioteca__cuenta');
  const cabecera = el('header', 'q-biblioteca__cabecera', el('h2', 'q-biblioteca__titulo', 'Tu biblioteca'), cuenta);

  return {
    titulo: 'Novelas',
    nodo: el('div', 'q-vista q-vista--inicio', cabecera, estanteria),
    recursos: [
      {
        clave: 'novelas',
        cada: CADA_DATOS,
        async pedir(senal) {
          const [novelas, lanzamientos] = await Promise.all([api.novelas(senal), api.lanzamientos(senal)]);
          const visibles = novelas.filter((n) => esVisible(n.slug));
          const fichas = await Promise.all(
            visibles.map(async ({ slug }): Promise<Ficha> => {
              const [libro, config] = await Promise.allSettled([api.libro(slug, senal), api.config(slug, senal)]);
              return { slug, libro: valor(libro), config: valor(config), lanzamiento: lanzamientos.find((l) => l.slug === slug) };
            }),
          );
          cuenta.textContent = visibles.length === 1 ? '1 novela' : `${visibles.length} novelas`;
          const tarjetas = fichas.map((f) => {
            const obra = obras.get(f.slug) ?? crearObra(f.slug);
            obras.set(f.slug, obra);
            obra.poner(f);
            return obra.raiz;
          });
          const vacio = estadoVacio({
            icono: 'library',
            texto: 'todavía no hay novelas: lanza la primera',
            pista: 'Aparecerán aquí, con su portada, en cuanto se cree su biblia.',
          });
          estanteria.replaceChildren(nueva, ...(tarjetas.length ? tarjetas : [vacio]));
        },
      },
    ],
  };
}
