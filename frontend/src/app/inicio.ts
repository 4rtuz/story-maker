// Inicio (RF-08): una entrada por novela de GET /novelas, con su cursor y los enlaces a su
// Progreso y a su Lectura, y el botón para lanzar una nueva.
import * as api from '../shared/api/cliente';
import { icono } from '../shared/iconos/trazados';
import { CADA_DATOS } from '../shared/sondeo';
import { el, enlaceBoton, esqueleto, estadoVacio, etiqueta, tarjeta } from '../shared/ui/componentes';
import type { Vista } from './rutas';

type Novela = api.Esquemas['CursorDeNovela'];

function entrada({ slug, cursor }: Novela): HTMLElement {
  const nombre = el('a', 'q-entrada__slug', icono('library'), slug);
  nombre.href = `#/novelas/${slug}/progreso`;
  const paso = cursor.ultimo_paso ?? 'ninguno todavía';
  return el(
    'article',
    'q-entrada',
    el('div', 'q-entrada__cabecera', el('h3', 'q-entrada__titulo', nombre), etiqueta(`capítulo ${cursor.capitulo}`)),
    el('p', 'q-entrada__meta', `fase ${cursor.fase}, último paso ${paso}, intento ${cursor.intento}`),
    el(
      'div',
      'q-entrada__acciones',
      enlaceBoton('Ver progreso', `#/novelas/${slug}/progreso`, { flecha: true }),
      enlaceBoton('Leer', `#/novelas/${slug}/lectura`, { flecha: true }),
    ),
  );
}

export function inicio(): Vista {
  const lista = tarjeta({ titulo: 'Todas las novelas', icono: 'library', tono: 'naranja' });
  lista.cuerpo.className = 'q-tarjeta__cuerpo q-entradas';
  lista.cuerpo.append(...[0, 1].map(() => esqueleto('q-esqueleto--entrada')));
  const acciones = el(
    'div',
    'q-vista__acciones',
    enlaceBoton('Lanzar una novela', '#/lanzar', { variante: 'primario', icono: 'rocket' }),
  );
  return {
    titulo: 'Novelas',
    nodo: el('div', 'q-vista q-vista--inicio', acciones, lista.raiz),
    recursos: [
      {
        clave: 'novelas',
        cada: CADA_DATOS,
        async pedir(senal) {
          const novelas = await api.novelas(senal);
          lista.contar(novelas.length);
          lista.cuerpo.replaceChildren(
            ...(novelas.length
              ? novelas.map(entrada)
              : [
                  estadoVacio({
                    icono: 'library',
                    texto: 'todavía no hay novelas: lanza la primera',
                    pista: 'Aparecerán aquí en cuanto novela nueva cree su workspace.',
                  }),
                ]),
          );
        },
      },
    ],
  };
}
