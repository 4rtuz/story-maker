// Las gráficas de las métricas de Langfuse (spec 0015): barras por capítulo y reparto por rol. Una
// sola serie y un solo tono en cada una: la identidad la da el eje, no el color. Cada barra se
// enfoca con el teclado y dice su valor; la tabla de debajo tiene los mismos datos.
import { el, tabla } from '../../shared/ui/componentes';
import { duracion, usd, type CosteDeRol, type PuntoDeCapitulo } from './metricas';

export type Medida = 'coste' | 'tiempo';

const valorDe = (p: PuntoDeCapitulo, m: Medida): number => (m === 'coste' ? p.coste : p.segundos);
const texto = (v: number, m: Medida): string => (m === 'coste' ? usd(v) : duracion(v));

export function barrasPorCapitulo(puntos: PuntoDeCapitulo[], medida: Medida): HTMLElement {
  const maximo = Math.max(...puntos.map((p) => valorDe(p, medida)), 0) || 1;
  const cima = puntos.findIndex((p) => valorDe(p, medida) === maximo);
  const columnas = puntos.map((p, i) => {
    const v = valorDe(p, medida);
    const col = el(
      'li',
      i === cima ? 'q-barras__col q-barras__col--cima' : 'q-barras__col',
      el('span', 'q-barras__valor', texto(v, medida)),
      el('span', 'q-barras__barra'),
      el('span', 'q-barras__eje', String(p.n)),
    );
    col.style.setProperty('--alto', String(v / maximo));
    col.tabIndex = 0;
    col.setAttribute('aria-label', `Capítulo ${p.n}: ${texto(v, medida)}, ${p.llamadas} llamadas`);
    return col;
  });
  const lista = el('ol', 'q-barras', ...columnas);
  lista.setAttribute('aria-label', medida === 'coste' ? 'Coste por capítulo' : 'Tiempo por capítulo');
  return lista;
}

export function barrasPorRol(roles: CosteDeRol[]): HTMLElement {
  return el(
    'ul',
    'q-roles',
    ...roles.map((r) => {
      const relleno = el('span', 'q-roles__relleno');
      relleno.style.setProperty('--ancho', String(r.fraccion));
      return el(
        'li',
        'q-roles__fila',
        el('span', 'q-roles__nombre', r.nombre),
        el('span', 'q-roles__pista', relleno),
        el('span', 'q-roles__valor', `${usd(r.coste)} · ${Math.round(r.fraccion * 100)} %`),
      );
    }),
  );
}

export function tablaPorCapitulo(puntos: PuntoDeCapitulo[]): HTMLElement {
  const detalles = el('details', 'q-detalles', el('summary', 'q-detalles__resumen', 'Ver los datos en una tabla'));
  detalles.append(
    tabla(
      'Consumo por capítulo',
      ['Capítulo', 'Coste', 'Tiempo', 'Llamadas'],
      puntos.map((p) => [String(p.n), usd(p.coste), duracion(p.segundos), String(p.llamadas)]),
    ),
  );
  return detalles;
}
