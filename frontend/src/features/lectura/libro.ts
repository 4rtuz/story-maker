// Portada, índice y ficha de la lectura web (docs/lectura-web.md), desde `GET …/libro`. Todo el
// texto viene del workspace y entra como nodo de texto (D56). Los enlaces son rutas de Lectura: al
// pulsarlos, el router abre el lector del capítulo. Los data-testid son el contrato de la
// validación visual (.claude/skills/validar-visual, e2e/libro.spec.ts): no se renombran.
import { hashDe } from '../../app/rutas';
import type * as api from '../../shared/api/cliente';
import { el } from '../../shared/ui/componentes';

type E = api.Esquemas;

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

export function libro(datos: E['Libro'], slug: string): HTMLElement {
  const titulo = (n: number): string => datos.capitulos.find((c) => c.capitulo === n)?.titulo ?? `Capítulo ${n}`;

  const portada = conId(el('header', 'q-libro__portada', conId(el('h3', 'q-libro__titulo', datos.titulo), 'portada-titulo')), 'portada');
  if (datos.dedicatoria) portada.append(conId(el('p', 'q-libro__dedicatoria', datos.dedicatoria), 'portada-dedicatoria'));

  const indice = conId(
    el(
      'nav',
      'q-libro__indice',
      el('h3', 'q-libro__seccion', 'Índice'),
      el('ol', 'q-libro__lista', ...datos.capitulos.map((c) => enlace(slug, c.capitulo, `${c.capitulo}. ${c.titulo}`, 'indice-capitulo'))),
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
  return conId(el('div', 'q-libro', portada, indice, ficha), 'libro');
}
