// El banner de la novela (RF-53): el texto en la mitad izquierda, sobre el tramo del degradado
// que mantiene --q-deco-banner-inicio, y las teselas solo en la mitad derecha.
import type { Esquemas } from '../api/cliente';
import { icono, type NombreDeIcono } from '../iconos/trazados';
import { el } from './componentes';

export interface ChipDeBanner {
  etiqueta: string;
  valor: string;
  icono: NombreDeIcono;
}

export interface DatosDeBanner {
  titular: string;
  subtitulo: string;
  chips: ChipDeBanner[];
}

type Subgenero = Esquemas['ParametrosObra']['subgenero'];

// Exhaustiva sobre el tipo generado: un subgénero nuevo en el backend rompe tsc aquí (VER-17).
const SUBGENEROS = {
  thriller_psicologico: 'Thriller psicológico',
  noir: 'Noir',
  domestic_suspense: 'Suspense doméstico',
  procedural: 'Procedimental',
} as const satisfies Record<Subgenero, string>;

/** Los datos del banner de Progreso y Lectura: lo que aún no ha llegado, no se muestra. */
export function datosDeBanner(
  slug: string,
  config: Esquemas['Config'] | undefined,
  cursor: Esquemas['Cursor'] | undefined,
): DatosDeBanner {
  const obra = config?.parametros_obra;
  return {
    titular: slug,
    subtitulo: obra
      ? `${SUBGENEROS[obra.subgenero]} · ${obra.num_capitulos} capítulos`.toLocaleUpperCase('es')
      : '',
    chips: cursor
      ? [
          { etiqueta: 'Fase', valor: cursor.fase, icono: 'activity' },
          { etiqueta: 'Capítulo', valor: String(cursor.capitulo), icono: 'book-open' },
          { etiqueta: 'Último paso', valor: cursor.ultimo_paso ?? 'ninguno', icono: 'history' },
          { etiqueta: 'Intento', valor: String(cursor.intento), icono: 'rocket' },
        ]
      : [],
  };
}

// Cuartos de círculo y cuadrados alternos: 4 filas por 6 columnas.
const TESELAS = 'cqcqqcqccqcqcqqcqccqcqqc';

const oculto = <T extends HTMLElement>(nodo: T, ocultar: boolean): T => {
  nodo.hidden = ocultar;
  return nodo;
};

export function banner({ titular, subtitulo, chips }: DatosDeBanner): HTMLElement {
  const lista = el(
    'ul',
    'q-banner__chips',
    ...chips.map((c) =>
      el('li', 'q-chip q-chip--banner', icono(c.icono), `${c.etiqueta}: `, el('b', '', c.valor)),
    ),
  );
  const teselas = el(
    'div',
    'q-banner__teselas',
    ...[...TESELAS].map((t, i) => el('span', `q-tesela q-tesela--${t === 'c' ? 'curva' : 'cuadro'} q-tesela--giro-${i % 4}`)),
  );
  teselas.setAttribute('aria-hidden', 'true');
  return el(
    'section',
    'q-banner',
    el(
      'div',
      'q-banner__texto',
      el('h2', 'q-banner__titular', titular),
      oculto(el('p', 'q-banner__subtitulo', subtitulo), !subtitulo),
      oculto(lista, !chips.length),
    ),
    teselas,
  );
}
