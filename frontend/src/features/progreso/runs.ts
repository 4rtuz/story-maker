// Los runs de la novela (RF-21): una subtarjeta por manifiesto, por run_id, con sus seis campos
// —run_id de título; fase y «árbol sucio» de etiquetas; capítulo, commit y fecha de metadatos—
// (spec 0004 §8.4, «Estructura»). Una tabla de seis columnas no cabe en media rejilla.
import type { Esquemas } from '../../shared/api/cliente';
import { el, etiqueta, subtarjeta } from '../../shared/ui/componentes';

/** `2026-09-24T10:00:00+02:00` como `2026-09-24 10:00`, con el valor exacto en `datetime`. */
function fecha(iso: string): HTMLElement {
  const t = el('time', 'q-fecha', iso.slice(0, 16).replace('T', ' '));
  t.dateTime = iso;
  return t;
}

export function listaDeRuns(manifiestos: Esquemas['Manifest'][]): HTMLElement {
  return el(
    'ol',
    'q-lista q-runs',
    ...manifiestos.map((m) => {
      const sha = el('code', 'q-sha', m.sha_commit.slice(0, 7));
      sha.title = m.sha_commit;
      const etiquetas = [etiqueta(m.fase), ...(m.sucio ? [etiqueta('árbol sucio')] : [])];
      return el(
        'li',
        'q-run',
        subtarjeta(
          el('div', 'q-subtarjeta__cabecera', el('strong', 'q-run__id', m.run_id), el('span', 'q-run__etiquetas', ...etiquetas)),
          el('p', 'q-subtarjeta__texto', `capítulo ${m.capitulo}, commit `, sha, ', ', fecha(m.creado)),
        ),
      );
    }),
  );
}
