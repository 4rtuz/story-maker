// El banner de la novela (RF-53): el texto en la mitad izquierda, sobre el tramo del degradado
// que mantiene --q-deco-banner-inicio, y las teselas solo en la mitad derecha.
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

// Cuartos de círculo y cuadrados alternos: 4 filas por 6 columnas.
const TESELAS = 'cqcqqcqccqcqcqqcqccqcqqc';

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
      el('p', 'q-banner__subtitulo', subtitulo),
      lista,
    ),
    teselas,
  );
}
