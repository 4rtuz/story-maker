// Progreso (spec 0015): la ficha de la novela con su portada, cuatro cifras, el proceso de creación,
// la tensión y las métricas de Langfuse. Cada recurso guarda su última respuesta válida y la vista
// se repinta con lo que haya: si una petición falla, lo anterior sigue en pantalla y el aviso lo
// pone el layout (RF-04).
import type { Vista } from '../../app/rutas';
import * as api from '../../shared/api/cliente';
import { lectorDelNavegador } from '../../shared/marca/lector-de-tokens';
import { estadoDeObra, SUBGENEROS } from '../../shared/obra';
import { CADA_DATOS, CADA_LOG, type Recurso } from '../../shared/sondeo';
import { el, enlaceBoton, esqueleto, estadoConPunto, estadoVacio, metrica, tabla, tarjeta, vacio } from '../../shared/ui/componentes';
import { portada, tituloDe, tituloProvisional } from '../../shared/ui/portada';
import { crearCreacion } from './creacion';
import { barrasPorCapitulo, barrasPorRol, tablaPorCapitulo, type Medida } from './graficas';
import { resumirCostes } from './metricas';
import { proceso } from './proceso';
import { resumir } from './resumen';
import { filasDeTension, graficaDeTension, serieDeTension } from './tension';

type E = api.Esquemas;

/** La leyenda: real y objetivo se distinguen por el trazo, no solo por el color (§8.4). */
function leyenda(): HTMLElement {
  const muestra = (clase: string, texto: string) => el('span', 'q-leyenda__item', el('span', `q-leyenda__trazo ${clase}`), texto);
  return el('p', 'q-leyenda', muestra('q-leyenda__trazo--real', 'Real'), muestra('q-leyenda__trazo--objetivo', 'Objetivo'));
}

function contenidoDeTension(real: (number | null)[], escaleta: E['Escaleta'] | null): HTMLElement[] {
  const serie = serieDeTension(real, escaleta);
  const avisos = [
    ...(serie.hayEscaleta ? [] : [vacio('el plan todavía no tiene escaleta')]),
    ...(serie.hayReal ? [] : [vacio('todavía no hay tensión puntuada')]),
  ];
  const datos = el('details', 'q-detalles', el('summary', 'q-detalles__resumen', 'Ver los datos en una tabla'));
  datos.append(tabla('Tensión por capítulo', ['Capítulo', 'Objetivo', 'Real'], filasDeTension(serie)));
  return [...avisos, leyenda(), el('div', 'q-tension__lienzo', graficaDeTension(serie, lectorDelNavegador())), datos];
}

interface Datos {
  estado?: E['Estado'];
  config?: E['Config'];
  checkpoint?: E['Checkpoint'] | null;
  escaleta?: E['Escaleta'] | null;
  libro?: E['Libro'];
  metricas?: E['InformeDeCostes'] | null;
  lanzamiento?: E['Lanzamiento'] | null;
}

/** Un dato pequeño de la tarjeta de Langfuse: rótulo encima y valor debajo. */
const dato = (rotulo: string, valor: string): HTMLElement => el('div', 'q-dato', el('dt', 'q-dato__rotulo', rotulo), el('dd', 'q-dato__valor', valor));

export function progreso({ slug }: { slug: string }): Vista {
  const datos: Datos = {};
  let medida: Medida = 'coste';

  const cubierta = portada({ slug, decorativa: true });
  const subtitulo = el('p', 'q-ficha__subtitulo');
  const titulo = el('h2', 'q-ficha__titulo', tituloProvisional(slug));
  const estadoObra = el('p', 'q-ficha__estado');
  const ficha = el(
    'header',
    'q-ficha',
    cubierta.raiz,
    el('div', 'q-ficha__texto', subtitulo, titulo, estadoObra, el('div', 'q-ficha__acciones', enlaceBoton('Leer la novela', `#/novelas/${slug}/lectura`, { variante: 'primario', icono: 'book-open' }))),
  );

  const capitulos = metrica({ etiqueta: 'Capítulos aceptados', icono: 'book-open', tono: 'naranja' });
  const palabras = metrica({ etiqueta: 'Palabras', icono: 'chart-line', tono: 'cian' });
  const coste = metrica({ etiqueta: 'Coste en Langfuse', icono: 'circle-dollar-sign', tono: 'naranja' });
  const tiempo = metrica({ etiqueta: 'Tiempo de escritura', icono: 'clock', tono: 'cian' });

  const tarjetaCreacion = tarjeta({ titulo: 'Proceso de creación', icono: 'sparkles', tono: 'naranja', clase: 'q-progreso__creacion' });
  const creacion = crearCreacion();
  tarjetaCreacion.cuerpo.append(esqueleto('q-esqueleto--lista'));
  const tarjetaTension = tarjeta({ titulo: 'Tensión', icono: 'chart-line', tono: 'cian', clase: 'q-progreso__tension' });
  tarjetaTension.cuerpo.append(esqueleto('q-esqueleto--grafica'));
  const tarjetaLangfuse = tarjeta({ titulo: 'Métricas de Langfuse', icono: 'activity', tono: 'cian', clase: 'q-progreso__langfuse' });
  tarjetaLangfuse.cuerpo.append(esqueleto('q-esqueleto--grafica'));

  const selector = el('div', 'q-selector');
  selector.setAttribute('role', 'group');
  selector.setAttribute('aria-label', 'Medida de la gráfica');
  const opcionesDeMedida: [Medida, string][] = [
    ['coste', 'Coste'],
    ['tiempo', 'Tiempo'],
  ];
  for (const [clave, rotulo] of opcionesDeMedida) {
    const b = el('button', 'q-selector__opcion', rotulo);
    b.type = 'button';
    b.dataset.medida = clave;
    b.addEventListener('click', () => {
      medida = clave;
      pintarLangfuse();
    });
    selector.append(b);
  }

  function pintarLangfuse(): void {
    const informe = datos.metricas;
    if (informe === undefined) return;
    if (informe === null || !informe.pasos.length) {
      coste.poner('—', 'sin datos todavía');
      tiempo.poner('—', 'sin datos todavía');
      tarjetaLangfuse.cuerpo.replaceChildren(
        estadoVacio({
          icono: 'activity',
          texto: 'Todavía no hay métricas de Langfuse',
          pista: 'Aparecerán en cuanto se cierre el primer capítulo.',
        }),
      );
      return;
    }
    const r = resumirCostes(informe);
    coste.poner(r.coste, `${r.medioPorCapitulo} por capítulo`);
    tiempo.poner(r.tiempo, `${r.llamadas} llamadas al modelo`);
    for (const b of selector.querySelectorAll<HTMLButtonElement>('button')) b.setAttribute('aria-pressed', String(b.dataset.medida === medida));
    const generado = el('time', '', new Date(informe.generado).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' }));
    generado.dateTime = informe.generado;
    tarjetaLangfuse.cuerpo.replaceChildren(
      el('dl', 'q-datos', dato('Llamadas', r.llamadas), dato('Tokens', r.tokens), dato('Caché leída', r.cache), dato('Coste medio por capítulo', r.medioPorCapitulo)),
      el(
        'div',
        'q-langfuse',
        el(
          'figure',
          'q-langfuse__figura',
          el('figcaption', 'q-langfuse__rotulo', medida === 'coste' ? 'Coste por capítulo' : 'Tiempo por capítulo', selector),
          r.capitulos.length ? barrasPorCapitulo(r.capitulos, medida) : vacio('ningún capítulo medido todavía'),
          ...(r.capitulos.length ? [tablaPorCapitulo(r.capitulos)] : []),
        ),
        el('figure', 'q-langfuse__figura', el('figcaption', 'q-langfuse__rotulo', 'Coste por rol'), barrasPorRol(r.roles)),
      ),
      el('p', 'q-langfuse__pie', 'Actualizado el ', generado, '. El coste lo calcula Langfuse por generación.'),
    );
  }

  function pintar(): void {
    const { estado, config, checkpoint, escaleta, libro, lanzamiento } = datos;
    const obra = config?.parametros_obra;
    const total = obra?.num_capitulos ?? 0;
    const cerrados = checkpoint?.capitulo ?? 0;
    const nombre = tituloDe(libro, slug);
    cubierta.poner(nombre, obra ? SUBGENEROS[obra.subgenero] : '');
    titulo.textContent = nombre;
    subtitulo.textContent = obra ? `${SUBGENEROS[obra.subgenero]} · ${total} capítulos` : '';
    if (config && checkpoint !== undefined && lanzamiento !== undefined) {
      estadoObra.replaceChildren(estadoConPunto(estadoDeObra(cerrados, total, lanzamiento)));
    }
    if (estado && config && checkpoint !== undefined) {
      const r = resumir(estado, config, checkpoint);
      capitulos.poner(r.numeroCerrados, r.cerrados);
      palabras.poner(r.palabras, r.palabrasObjetivo);
    }
    if (estado && config && checkpoint !== undefined && escaleta !== undefined && lanzamiento !== undefined) {
      const p = proceso({ total, hayEscaleta: escaleta !== null, cerrados, cursor: estado.cursor, lanzamiento });
      if (!creacion.raiz.isConnected) tarjetaCreacion.cuerpo.replaceChildren(creacion.raiz);
      creacion.poner(p, cerrados >= total ? `${total} capítulos` : `Capítulo ${Math.min(cerrados + 1, total)} de ${total}`);
    }
    if (estado && escaleta !== undefined) tarjetaTension.cuerpo.replaceChildren(...contenidoDeTension(estado.tension_real, escaleta));
    pintarLangfuse();
  }

  const recurso = (clave: string, pedir: (senal: AbortSignal) => Promise<void>, cada = CADA_DATOS): Recurso => ({
    clave,
    cada,
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
      ficha,
      el('div', 'q-metricas', capitulos.raiz, palabras.raiz, coste.raiz, tiempo.raiz),
      el('div', 'q-rejilla', tarjetaCreacion.raiz, tarjetaTension.raiz),
      tarjetaLangfuse.raiz,
    ),
    recursos: [
      recurso('estado', async (s) => void (datos.estado = await api.estado(slug, s))),
      recurso('config', async (s) => void (datos.config = await api.config(slug, s))),
      recurso('escaleta', async (s) => void (datos.escaleta = await api.escaleta(slug, s))),
      recurso('checkpoint', async (s) => void (datos.checkpoint = await api.checkpoint(slug, s))),
      recurso('libro', async (s) => void (datos.libro = await api.libro(slug, s))),
      recurso('metricas', async (s) => void (datos.metricas = await api.metricas(slug, s))),
      // El lanzamiento cambia de paso a menudo: a la cadencia del log, para que el proceso se note vivo.
      // La lista y no `/lanzamientos/{slug}`: una novela que no se lanzó desde el panel no da un 404.
      recurso('lanzamiento', async (s) => void (datos.lanzamiento = (await api.lanzamientos(s)).find((l) => l.slug === slug) ?? null), CADA_LOG),
    ],
  };
}
