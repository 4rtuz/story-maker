// Lanzar (spec 0015, RF-09, RF-10): un chat pregunta lo que necesita `novela producir` y el resumen
// lanza la novela en el backend (POST /lanzamientos) con un clic. Debajo, el tablero de lanzamientos
// por fase, con los botones de detener y reanudar. Ni órdenes, ni registro de sesiones, ni slugs.
import type { Vista } from '../../app/rutas';
import * as api from '../../shared/api/cliente';
import type { Esquemas } from '../../shared/api/cliente';
import { ErrorDeApi } from '../../shared/api/errores';
import { icono } from '../../shared/iconos/trazados';
import { CADA_DATOS, CADA_LOG } from '../../shared/sondeo';
import { boton, el, enlaceBoton, esqueleto } from '../../shared/ui/componentes';
import { portada, tituloProvisional } from '../../shared/ui/portada';
import { esVisible } from '../../shared/visibles';
import { inicial, pregunta, responder, resumen, type Conversacion } from './conversacion';
import { agrupar, pasoLegible } from './tablero';
import { peticion } from './validacion';

type Fila = Esquemas['Lanzamiento'];

/** Lo que tarda el asistente en «escribir» antes de cada mensaje: da ritmo, no espera a nada. */
const PAUSA_MS = 450;

const motivo = (error: unknown): string => (error instanceof ErrorDeApi ? error.detalle : String(error));

function crearChat(existentes: () => string[] | null, alLanzar: (f: Fila) => void): HTMLElement {
  let conversacion: Conversacion = inicial();
  let temporizador: ReturnType<typeof setTimeout> | undefined;

  const mensajes = el('div', 'q-chat__mensajes');
  mensajes.setAttribute('role', 'log');
  mensajes.setAttribute('aria-live', 'polite');
  mensajes.setAttribute('aria-label', 'Conversación');
  const opciones = el('div', 'q-chat__opciones');
  const texto = el('textarea', 'q-chat__texto');
  texto.rows = 1;
  texto.setAttribute('aria-label', 'Tu respuesta');
  texto.placeholder = 'Escribe tu respuesta…';
  const enviar = el('button', 'q-chat__enviar', icono('send'), el('span', 'q-oculto-visual', 'Enviar'));
  enviar.type = 'submit';
  const formulario = el('form', 'q-chat__entrada', texto, enviar);
  const alPie = (): void => void (mensajes.scrollTop = mensajes.scrollHeight);

  function burbuja(de: 'bot' | 'tu', ...hijos: (Node | string)[]): HTMLElement {
    const nodo = el('div', `q-burbuja q-burbuja--${de}`, ...hijos);
    mensajes.append(nodo);
    alPie();
    return nodo;
  }

  /** El asistente «escribe» un momento y luego dice lo suyo. */
  function decir(pintar: () => void): void {
    const escribiendo = burbuja('bot', el('span', 'q-escribiendo', el('span'), el('span'), el('span')));
    escribiendo.classList.add('q-burbuja--escribiendo');
    escribiendo.setAttribute('aria-hidden', 'true');
    clearTimeout(temporizador);
    temporizador = setTimeout(() => {
      escribiendo.remove();
      pintar();
    }, PAUSA_MS);
  }

  function preguntar(): void {
    const p = pregunta(conversacion, existentes() ?? []);
    opciones.replaceChildren();
    formulario.hidden = true;
    decir(() => {
      if (!p) return mostrarResumen();
      burbuja('bot', p.texto);
      const chips = [...p.opciones, ...(p.omitible ? [{ valor: '', rotulo: 'Omitir' }] : [])];
      opciones.replaceChildren(
        ...chips.map((o) => {
          const b = el('button', o.valor ? 'q-chip-opcion' : 'q-chip-opcion q-chip-opcion--omitir', o.rotulo);
          b.type = 'button';
          b.addEventListener('click', () => contestar(o.valor, o.rotulo || 'Omitir'));
          return b;
        }),
      );
      formulario.hidden = p.paso === 'regalo';
      alPie(); // las opciones acortan el registro: se baja otra vez para que se vea la pregunta
      texto.value = '';
      texto.placeholder = p.multilinea ? 'Escribe tu respuesta… (Mayús + Intro para otra línea)' : 'Escribe tu respuesta…';
      if (!formulario.hidden) texto.focus();
    });
  }

  function contestar(valor: string, eco: string): void {
    burbuja('tu', eco);
    const r = responder(conversacion, valor, existentes());
    if (r.error) {
      opciones.replaceChildren();
      formulario.hidden = true;
      decir(() => {
        burbuja('bot', `No me cuadra: ${r.error}.`).classList.add('q-burbuja--error');
        preguntar();
      });
      return;
    }
    conversacion = r.conversacion;
    preguntar();
  }

  function mostrarResumen(): void {
    opciones.replaceChildren();
    formulario.hidden = true;
    const lanzarBoton = boton('Lanzar novela', { icono: 'rocket' });
    const deNuevo = boton('Empezar de nuevo', { variante: 'secundario', icono: 'rotate-ccw' });
    const filas = resumen(conversacion).map(([rotulo, valor]) => el('div', 'q-resumen__fila', el('dt', '', rotulo), el('dd', '', valor)));
    burbuja(
      'bot',
      'Perfecto. Esto es lo que voy a escribir:',
      el('dl', 'q-resumen', ...filas),
      el('div', 'q-resumen__acciones', lanzarBoton, deNuevo),
    );
    lanzarBoton.focus();
    deNuevo.addEventListener('click', () => {
      conversacion = inicial();
      mensajes.replaceChildren();
      preguntar();
    });
    lanzarBoton.addEventListener('click', () => {
      lanzarBoton.disabled = true;
      deNuevo.disabled = true;
      api
        .lanzar(peticion(conversacion.campos))
        .then((fila) => {
          alLanzar(fila);
          lanzarBoton.remove();
          decir(() => {
            burbuja(
              'bot',
              '¡En marcha! Primero preparo la biblia y después escribo capítulo a capítulo. Puedes seguirlo aquí debajo o en su página.',
              el('div', 'q-resumen__acciones', enlaceBoton('Ver su progreso', `#/novelas/${fila.slug}/progreso`, { flecha: true })),
            );
            deNuevo.disabled = false;
          });
        })
        .catch((error: unknown) => {
          lanzarBoton.disabled = false;
          deNuevo.disabled = false;
          burbuja('bot', `No he podido lanzarla: ${motivo(error)}.`).classList.add('q-burbuja--error');
        });
    });
  }

  formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();
    const valor = texto.value;
    if (!/\S/.test(valor)) return;
    contestar(valor, valor.trim());
  });
  texto.addEventListener('keydown', (evento) => {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault();
      formulario.requestSubmit();
    }
  });

  preguntar();
  return el(
    'section',
    'q-chat',
    el(
      'header',
      'q-chat__cabecera',
      el('span', 'q-chat__avatar', icono('sparkles')),
      el('div', '', el('h2', 'q-chat__titulo', 'Nueva novela'), el('p', 'q-chat__subtitulo', 'Unas preguntas y me pongo a escribir')),
    ),
    mensajes,
    opciones,
    formulario,
  );
}

export function lanzar(): Vista {
  let existentes: string[] | null = null;
  let actuales: Fila[] = [];

  const aviso = el('p', 'q-tablero__aviso');
  aviso.setAttribute('role', 'status');
  const columnas = el('div', 'q-tablero__columnas', esqueleto('q-esqueleto--tablero'));

  /** Una petición de un botón: deshabilitado mientras dura, y su resultado en el tablero al volver. */
  async function accion(b: HTMLButtonElement, pedir: () => Promise<Fila>, exito: string): Promise<void> {
    b.disabled = true;
    try {
      const nuevo = await pedir();
      pintar([nuevo, ...actuales.filter((l) => l.slug !== nuevo.slug)]);
      aviso.textContent = exito;
    } catch (error) {
      aviso.textContent = motivo(error);
    } finally {
      b.disabled = false;
    }
  }

  function tarjeta(l: Fila): HTMLElement {
    const titulo = tituloProvisional(l.slug);
    const acciones = el('div', 'q-tarea__acciones');
    if (l.estado === 'en_marcha' && !l.detener_pedido) {
      const b = boton('Detener', { variante: 'secundario', icono: 'pause' });
      b.append(el('span', 'q-oculto-visual', ` ${titulo}`));
      b.addEventListener('click', () => void accion(b, () => api.detener(l.slug), `${titulo}: se pausará al terminar el capítulo en curso`));
      acciones.append(b);
    } else if (l.estado !== 'en_marcha' && l.estado !== 'terminado') {
      const b = boton('Reanudar', { variante: 'secundario', icono: 'rocket' });
      b.append(el('span', 'q-oculto-visual', ` ${titulo}`));
      b.addEventListener('click', () => void accion(b, () => api.reanudar(l.slug), `${titulo}: reanudada`));
      acciones.append(b);
    }
    const ver = el('a', 'q-tarea__ver', l.estado === 'terminado' ? 'Leer' : 'Ver progreso');
    ver.href = `#/novelas/${l.slug}/${l.estado === 'terminado' ? 'lectura' : 'progreso'}`;
    acciones.append(ver);
    const paso = el('p', 'q-tarea__paso', ...(l.estado === 'en_marcha' ? [el('span', 'q-girando')] : []), pasoLegible(l));
    return el(
      'article',
      `q-tarea q-tarea--${l.estado}`,
      portada({ slug: l.slug, tamano: 'mini', decorativa: true }).raiz,
      el('div', 'q-tarea__cuerpo', el('h4', 'q-tarea__titulo', titulo), paso, acciones),
    );
  }

  function pintar(lanzamientos: Fila[]): void {
    actuales = lanzamientos;
    columnas.replaceChildren(
      ...agrupar(lanzamientos.filter((l) => esVisible(l.slug))).map(({ clave, titulo, filas }) => {
        const columna = el(
          'section',
          `q-columna q-columna--${clave}`,
          el('header', 'q-columna__cabecera', el('h3', 'q-columna__titulo', titulo), el('span', 'q-columna__cuenta', String(filas.length))),
          ...(filas.length ? filas.map(tarjeta) : [el('p', 'q-columna__vacia', 'Nada por aquí')]),
        );
        columna.dataset.columna = clave;
        columna.setAttribute('aria-label', titulo);
        return columna;
      }),
    );
  }

  const tablero = el(
    'section',
    'q-tablero',
    el('header', 'q-tablero__cabecera', el('h2', 'q-tablero__titulo', 'Lanzamientos'), aviso),
    columnas,
  );
  tablero.setAttribute('aria-label', 'Lanzamientos');

  return {
    titulo: 'Lanzar',
    nodo: el('div', 'q-vista q-vista--lanzar', crearChat(() => existentes, (f) => pintar([f, ...actuales.filter((l) => l.slug !== f.slug)])), tablero),
    recursos: [
      {
        clave: 'novelas',
        cada: CADA_DATOS,
        async pedir(senal) {
          try {
            existentes = (await api.novelas(senal)).map((n) => n.slug);
          } catch (error) {
            existentes = null; // no ha respondido o ha fallado: se lanza y el backend decide (D43)
            throw error;
          }
        },
      },
      {
        clave: 'lanzamientos',
        cada: CADA_LOG,
        async pedir(senal) {
          pintar(await api.lanzamientos(senal));
        },
      },
    ],
  };
}
