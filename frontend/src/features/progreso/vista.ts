// Progreso (RF-17 a RF-23, RF-53, RF-54): banner, fila de métricas y rejilla de tarjetas. Cada
// recurso guarda su última respuesta válida y la vista se repinta con lo que haya: si una
// petición falla, lo anterior sigue en pantalla y el aviso lo pone el layout (RF-04).
import type { Vista } from '../../app/rutas';
import * as api from '../../shared/api/cliente';
import { CADA_DATOS, type Recurso } from '../../shared/sondeo';
import { banner, datosDeBanner } from '../../shared/ui/banner';
import { el, esqueleto, estadoVacio, etiqueta, metrica, subtarjeta, tarjeta, vacio } from '../../shared/ui/componentes';
import { hilosAbiertos, resumir } from './resumen';
import { listaDeRuns } from './runs';

type E = api.Esquemas;

interface Datos {
  estado?: E['Estado'];
  config?: E['Config'];
  checkpoint?: E['Checkpoint'] | null;
  capitulos?: E['FrontmatterCapitulo'][];
  runs?: E['Manifest'][];
  escaleta?: E['Escaleta'] | null;
}

export function progreso({ slug }: { slug: string }): Vista {
  const datos: Datos = {};
  const cabecera = el('div', 'q-progreso__banner', banner(datosDeBanner(slug, undefined, undefined)));

  const cerrados = metrica({ etiqueta: 'Capítulos cerrados', icono: 'book-open', tono: 'naranja' });
  const palabras = metrica({ etiqueta: 'Palabras', icono: 'chart-line', tono: 'cian' });
  const desviacion = metrica({ etiqueta: 'Desviación', icono: 'activity', tono: 'naranja' });
  const hilos = metrica({ etiqueta: 'Hilos abiertos', icono: 'list-tree', tono: 'cian' });

  const tarjetaHilos = tarjeta({ titulo: 'Hilos abiertos', icono: 'list-tree', tono: 'naranja' });
  tarjetaHilos.cuerpo.append(esqueleto('q-esqueleto--lista'));
  const tarjetaRuns = tarjeta({ titulo: 'Runs', icono: 'history', tono: 'cian' });
  tarjetaRuns.cuerpo.append(esqueleto('q-esqueleto--lista'));

  function pintar(): void {
    const { estado, config, checkpoint, capitulos, runs } = datos;
    cabecera.replaceChildren(banner(datosDeBanner(slug, config, estado?.cursor)));
    if (estado && config && checkpoint !== undefined) {
      const r = resumir(estado, config, checkpoint);
      const enCurso = capitulos?.filter((c) => c.capitulo > (checkpoint?.capitulo ?? 0)).length;
      cerrados.poner(r.numeroCerrados, enCurso ? `${r.cerrados}; ${enCurso} en curso` : r.cerrados);
      palabras.poner(r.palabras, r.palabrasObjetivo);
      desviacion.poner(r.desviacion, 'frente al plan');
    }
    if (estado) {
      const abiertos = hilosAbiertos(estado);
      hilos.poner(String(abiertos.length));
      tarjetaHilos.contar(abiertos.length);
      tarjetaHilos.cuerpo.replaceChildren(
        abiertos.length
          ? el(
              'ul',
              'q-lista',
              ...abiertos.map((h) =>
                el(
                  'li',
                  '',
                  subtarjeta(
                    el('div', 'q-subtarjeta__cabecera', el('strong', '', h.id), etiqueta(`abierto en ${h.abierto_en}`)),
                    el('p', 'q-subtarjeta__texto', h.descripcion),
                  ),
                ),
              ),
            )
          : vacio('no hay hilos abiertos'),
      );
    }
    if (runs) {
      tarjetaRuns.contar(runs.length);
      const desplazable = el('div', 'q-desplazable', listaDeRuns(runs));
      desplazable.tabIndex = 0; // se desplaza con teclado
      desplazable.setAttribute('aria-label', 'Runs de la novela');
      tarjetaRuns.cuerpo.replaceChildren(
        runs.length
          ? desplazable
          : estadoVacio({ icono: 'history', texto: 'sin runs todavía', pista: 'El primer run aparece con el primer paso del bucle.' }),
      );
    }
  }

  const recurso = (clave: string, pedir: (senal: AbortSignal) => Promise<void>): Recurso => ({
    clave,
    cada: CADA_DATOS,
    async pedir(senal) {
      await pedir(senal);
      pintar();
    },
  });

  return {
    titulo: 'Progreso',
    nodo: el(
      'div',
      'q-vista q-vista--progreso',
      cabecera,
      el('div', 'q-metricas', cerrados.raiz, palabras.raiz, desviacion.raiz, hilos.raiz),
      el('div', 'q-rejilla', tarjetaHilos.raiz, tarjetaRuns.raiz),
    ),
    recursos: [
      recurso('estado', async (s) => void (datos.estado = await api.estado(slug, s))),
      recurso('config', async (s) => void (datos.config = await api.config(slug, s))),
      recurso('escaleta', async (s) => void (datos.escaleta = await api.escaleta(slug, s))),
      recurso('checkpoint', async (s) => void (datos.checkpoint = await api.checkpoint(slug, s))),
      recurso('capitulos', async (s) => void (datos.capitulos = await api.capitulos(slug, s))),
      recurso('runs', async (s) => void (datos.runs = await api.runs(slug, s))),
    ],
  };
}
