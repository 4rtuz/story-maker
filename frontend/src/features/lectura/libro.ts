// Portada, índice y ficha de la lectura web (docs/lectura-web.md), desde `GET …/libro`. Todo el
// texto viene del workspace y entra como nodo de texto (D56). Los enlaces son rutas de Lectura: al
// pulsarlos, el router abre el lector del capítulo. Los data-testid son el contrato de la
// validación visual (.claude/skills/validar-visual, e2e/libro.spec.ts): no se renombran.
import { hashDe } from '../../app/rutas';
import { urlDePdf, type Esquemas } from '../../shared/api/cliente';
import { el, enlaceBoton, vacio } from '../../shared/ui/componentes';

type E = Esquemas;

function conId<T extends HTMLElement>(nodo: T, testid: string, datos: Record<string, string> = {}): T {
  nodo.dataset.testid = testid;
  Object.assign(nodo.dataset, datos);
  return nodo;
}

function enlace(slug: string, n: number, texto: string, testid: string, nombre?: string): HTMLElement {
  const a = el('a', 'q-libro__enlace', texto);
  a.href = hashDe({ vista: 'lectura', slug, capitulo: n });
  if (nombre) {
    a.setAttribute('aria-label', nombre);
    a.title = nombre;
  }
  return el('li', '', conId(a, testid, { destino: String(n) }));
}

/** `cubierta`, si llega, es la ilustración de la portada (spec 0015): va a la izquierda del título. */
export function libro(datos: E['Libro'], slug: string, cubierta?: HTMLElement, subtitulo = ''): HTMLElement {
  const titulo = (n: number): string => datos.capitulos.find((c) => c.capitulo === n)?.titulo ?? `Capítulo ${n}`;

  const presentacion = el(
    'div',
    'q-libro__presentacion',
    ...(subtitulo ? [el('p', 'q-libro__subtitulo', subtitulo)] : []),
    conId(el('h2', 'q-libro__titulo', datos.titulo), 'portada-titulo'),
  );
  if (datos.dedicatoria) presentacion.append(conId(el('p', 'q-libro__dedicatoria', datos.dedicatoria), 'portada-dedicatoria'));
  const primero = datos.capitulos[0];
  if (primero) {
    const empezar = enlaceBoton('Empezar a leer', hashDe({ vista: 'lectura', slug, capitulo: primero.capitulo }), { variante: 'primario', icono: 'book-open' });
    const pdf = conId(enlaceBoton('Descargar PDF', urlDePdf(slug), { icono: 'download' }), 'portada-pdf');
    pdf.setAttribute('download', `${slug}.pdf`);
    presentacion.append(
      el('p', 'q-libro__cuantos', `${datos.capitulos.length} ${datos.capitulos.length === 1 ? 'capítulo' : 'capítulos'} para leer`),
      el('div', 'q-libro__acciones', conId(empezar, 'portada-empezar'), pdf),
    );
  }
  const portada = conId(el('header', 'q-libro__portada', ...(cubierta ? [cubierta] : []), presentacion), 'portada');

  const indice = conId(
    el(
      'nav',
      'q-libro__indice',
      el('h3', 'q-libro__seccion', 'Índice'),
      datos.capitulos.length
        ? el('ol', 'q-libro__lista', ...datos.capitulos.map((c) => enlace(slug, c.capitulo, `${c.capitulo}. ${c.titulo}`, 'indice-capitulo')))
        : vacio('ningún capítulo cerrado todavía'),
    ),
    'indice',
  );
  indice.setAttribute('aria-label', 'Índice');

  const grupo = (nombre: string, tipo: string, entradas: E['EntradaDeFicha'][]): HTMLElement[] =>
    entradas.length === 0
      ? []
      : [
          el('h4', 'q-libro__grupo', nombre),
          el(
            'ul',
            'q-libro__lista',
            ...entradas.map((e) =>
              conId(
                el(
                  'li',
                  'q-libro__entrada',
                  el('strong', '', e.nombre),
                  ...(e.detalle ? [el('span', 'q-libro__detalle', e.detalle)] : []),
                  el('span', 'q-libro__aparece', 'Aparece en los capítulos'),
                  el('ul', 'q-libro__apariciones', ...e.capitulos.map((n) => enlace(slug, n, String(n), 'ficha-enlace', `Capítulo ${n} — ${titulo(n)}`))),
                ),
                'ficha-entrada',
                { entidad: e.id, tipo },
              ),
            ),
          ),
        ];

  const ficha = conId(
    el(
      'section',
      'q-libro__ficha',
      el('h3', 'q-libro__seccion', 'Personajes y lugares'),
      ...grupo('Personajes', 'personaje', datos.personajes),
      ...grupo('Lugares', 'lugar', datos.lugares),
    ),
    'ficha',
  );
  return conId(el('div', 'q-libro', portada, el('div', 'q-libro__cuerpo', indice, ficha)), 'libro');
}
