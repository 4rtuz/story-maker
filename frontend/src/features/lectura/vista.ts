// Lectura (RF-24 a RF-31, RF-58): la estantería con un volumen por capítulo, su lista HTML
// equivalente y el lector en un diálogo modal. La selección vive aquí y la ruta lleva el capítulo
// abierto (RF-10). Un capítulo solo se pide si está cerrado, y no antes de conocer el checkpoint
// (RF-27, D8, VAL-7).
import type { Ruta, Vista } from '../../app/rutas';
import * as api from '../../shared/api/cliente';
import { ErrorDeApi } from '../../shared/api/errores';
import { lectorDelNavegador } from '../../shared/marca/lector-de-tokens';
import { CADA_DATOS, type Recurso } from '../../shared/sondeo';
import { banner, datosDeBanner } from '../../shared/ui/banner';
import { aviso, boton, el, esqueleto, estadoVacio, etiqueta, tarjeta, vacio } from '../../shared/ui/componentes';
import { disposicion } from './disposicion';
import type { Escena, FabricaDeRenderer } from './escena';
import { estadosDeVolumen, TEXTO_DE_ESTADO, type EstadoDeVolumen } from './estados';
import { libro } from './libro';
import { tecla } from './navegacion';

type E = api.Esquemas;

interface Datos {
  config?: E['Config'];
  escaleta?: E['Escaleta'] | null;
  checkpoint?: E['Checkpoint'] | null;
  capitulos?: E['FrontmatterCapitulo'][];
  libro?: E['Libro'];
}

const FOCUSABLES = 'button, [href], [tabindex]:not([tabindex="-1"])';

const reducirMovimiento = (): boolean =>
  typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function lectura(
  { slug, capitulo }: { slug: string; capitulo?: number },
  navegar: (ruta: Ruta) => void,
  opciones: { crearRenderer?: FabricaDeRenderer } = {},
): Vista {
  const datos: Datos = {};
  let seleccion = capitulo ?? 1;
  let abierto: number | null = capitulo ?? null;
  let texto: { n: number; nodo: HTMLElement } | { n: number; error: string } | null = null;
  let peticion: { n: number; control: AbortController } | null = null;
  let escena3d: Escena | null = null;
  let estadoEscena: 'sin-empezar' | 'cargando' | 'lista' | 'no-disponible' = 'sin-empezar';
  let montada = true;

  const cabecera = el('div', 'q-progreso__banner', banner(datosDeBanner(slug, undefined, undefined)));
  const tarjetaEscena = tarjeta({ titulo: 'Estantería', icono: 'library', tono: 'naranja', clase: 'q-lectura__estanteria' });
  const escena = el('div', 'q-escena', esqueleto('q-esqueleto--escena'));
  tarjetaEscena.cuerpo.append(escena);
  const tarjetaLista = tarjeta({ titulo: 'Capítulos', icono: 'book-open', tono: 'cian', clase: 'q-lectura__lista' });
  tarjetaLista.cuerpo.append(esqueleto('q-esqueleto--lista'));
  // Portada, índice y ficha (docs/lectura-web.md): se rehace solo si cambia el libro.
  const tarjetaLibro = tarjeta({ titulo: 'Libro', icono: 'book-open', tono: 'naranja', clase: 'q-lectura__libro' });
  tarjetaLibro.cuerpo.append(esqueleto('q-esqueleto--lista'));
  let libroPintado = '';
  const lista = el('ol', 'q-volumenes');
  lista.setAttribute('aria-label', 'Capítulos de la novela');
  const capa = el('div', 'q-lector-capa');
  capa.hidden = true;

  const total = (): number => datos.config?.parametros_obra.num_capitulos ?? 0;
  const estados = (): EstadoDeVolumen[] =>
    estadosDeVolumen(total(), datos.checkpoint ?? null, (datos.capitulos ?? []).map((c) => c.capitulo));
  const titulo = (n: number): string => datos.capitulos?.find((c) => c.capitulo === n)?.titulo ?? `Capítulo ${n}`;
  const botonDe = (n: number): HTMLButtonElement | null => lista.querySelector(`[data-capitulo="${n}"]`);
  const abrir = (n: number): void => navegar({ vista: 'lectura', slug, capitulo: n });
  const cerrar = (): void => navegar({ vista: 'lectura', slug });

  function seleccionar(n: number, enfocar = false): void {
    if (n !== seleccion) escena3d?.seleccionar(n);
    seleccion = n;
    escena.dataset.seleccion = String(n);
    for (const b of lista.querySelectorAll<HTMLButtonElement>('[data-capitulo]')) {
      const actual = b.dataset.capitulo === String(n);
      b.tabIndex = actual ? 0 : -1;
      if (actual) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    }
    if (enfocar) botonDe(n)?.focus();
  }

  lista.addEventListener('keydown', (evento) => {
    const pulsacion = tecla(evento.key, seleccion, total());
    if (!pulsacion || pulsacion.accion === 'cerrar') return;
    evento.preventDefault();
    if (pulsacion.accion === 'abrir') abrir(pulsacion.seleccion);
    else seleccionar(pulsacion.seleccion, true);
  });

  /** Construye la lista si cambia el número de capítulos; si no, actualiza cada elemento sin
   * rehacerlo, para no perder el foco en cada ronda. */
  function pintarLista(): void {
    const n = total();
    if (lista.children.length !== n) {
      lista.replaceChildren(
        ...Array.from({ length: n }, (_, i) => {
          const b = el('button', 'q-volumen');
          b.type = 'button';
          b.dataset.capitulo = String(i + 1);
          b.addEventListener('focus', () => seleccionar(i + 1));
          b.addEventListener('click', () => {
            seleccionar(i + 1);
            abrir(i + 1);
          });
          return el('li', '', b);
        }),
      );
      seleccion = Math.min(Math.max(1, seleccion), Math.max(1, n));
    }
    estados().forEach((estado, i) => {
      const b = botonDe(i + 1);
      b?.replaceChildren(
        el('span', 'q-volumen__numero', String(i + 1)),
        el('span', 'q-volumen__titulo', titulo(i + 1)),
        etiqueta(TEXTO_DE_ESTADO[estado]),
      );
      if (b) b.dataset.estado = estado;
    });
    seleccionar(seleccion);
  }

  /** Three.js y la escena llegan en su propio chunk al entrar en Lectura (RNF-02). */
  async function iniciarEscena(): Promise<void> {
    estadoEscena = 'cargando';
    const modulo = await import('./escena');
    if (!montada) return;
    escena.replaceChildren();
    escena3d = modulo.crearEscena({
      contenedor: escena,
      lector: lectorDelNavegador(),
      crearRenderer: opciones.crearRenderer ?? modulo.rendererWebGL,
      reducirMovimiento,
      alSeleccionar: (n) => seleccionar(n),
      alAbrir: abrir,
      alFallar: sinEscena,
    });
    if (!escena3d) return sinEscena();
    estadoEscena = 'lista';
    pintarEscena();
  }

  /** Sin WebGL, o con el contexto perdido: queda la lista, que tiene lo mismo (RF-29). */
  function sinEscena(): void {
    escena3d = null;
    estadoEscena = 'no-disponible';
    escena.replaceChildren(
      estadoVacio({
        icono: 'library',
        texto: 'vista 3D no disponible',
        pista: 'La lista de capítulos tiene los mismos volúmenes y abre el lector.',
      }),
    );
  }

  function pintarEscena(): void {
    escena3d?.actualizar(estados(), disposicion(total(), datos.escaleta?.actos ?? null), seleccion);
  }

  function pintar(): void {
    cabecera.replaceChildren(banner(datosDeBanner(slug, datos.config, undefined)));
    if (!datos.config) return;
    escena.dataset.volumenes = String(total());
    pintarLista();
    if (datos.libro && JSON.stringify(datos.libro) !== libroPintado) {
      libroPintado = JSON.stringify(datos.libro);
      tarjetaLibro.cuerpo.replaceChildren(libro(datos.libro, slug));
    }
    if (estadoEscena === 'sin-empezar') void iniciarEscena();
    pintarEscena();
    if (datos.checkpoint === undefined || datos.capitulos === undefined) return;
    const sinCerrados = !estados().includes('cerrado');
    tarjetaLista.cuerpo.replaceChildren(...(sinCerrados ? [vacio('ningún capítulo cerrado todavía')] : []), lista);
    pintarLector();
  }

  async function pedirCapitulo(n: number): Promise<void> {
    const control = new AbortController();
    peticion = { n, control };
    try {
      // markdown-it y el lector llegan en el chunk de Lectura, con la escena (RNF-02).
      const [markdown, { cuerpoDeCapitulo }] = await Promise.all([api.capitulo(slug, n, control.signal), import('./lector')]);
      texto = { n, nodo: cuerpoDeCapitulo(markdown) };
    } catch (error) {
      if (!(error instanceof ErrorDeApi)) return; // abortada al cerrar o al salir
      texto = { n, error: error.message };
    } finally {
      if (peticion?.control === control) peticion = null;
    }
    pintarLector();
  }

  function pintarLector(): void {
    if (abierto === null) {
      peticion?.control.abort();
      peticion = null;
      if (!capa.hidden) {
        capa.hidden = true;
        capa.replaceChildren();
        botonDe(seleccion)?.focus();
      }
      return;
    }
    const n = abierto;
    const conocido = datos.checkpoint !== undefined && datos.capitulos !== undefined && datos.config !== undefined;
    const cerrado = conocido && estados()[n - 1] === 'cerrado';
    const fase = !conocido ? 'esperando' : !cerrado ? 'no-disponible' : texto?.n === n ? 'texto' : 'cargando';
    if (fase === 'cargando' && peticion?.n !== n) void pedirCapitulo(n);
    // Cada ronda repinta la vista: el diálogo solo se rehace si cambia lo que muestra, para no
    // perder el desplazamiento de la lectura.
    const nuevaFirma = `${n}|${fase}|${titulo(n)}`;
    if (!capa.hidden && firma === nuevaFirma) return;
    firma = nuevaFirma;
    let cuerpo: HTMLElement;
    if (fase === 'no-disponible') cuerpo = vacio('capítulo no disponible todavía');
    else if (fase === 'texto' && texto) cuerpo = 'error' in texto ? aviso(texto.error) : texto.nodo;
    else cuerpo = esqueleto('q-esqueleto--lector');
    mostrarDialogo(n, cuerpo);
  }

  let firma = '';

  function mostrarDialogo(n: number, cuerpo: HTMLElement): void {
    const encabezado = el('h2', 'q-lector__titulo');
    encabezado.id = 'q-lector-titulo';
    encabezado.dataset.testid = 'lector-titulo';
    encabezado.textContent = titulo(n); // el título lo escribe un agente: siempre como texto (D56)
    const cerrarBoton = boton('Cerrar', { variante: 'secundario' });
    cerrarBoton.addEventListener('click', cerrar);
    const desplazable = el('div', 'q-lector__cuerpo', cuerpo);
    desplazable.tabIndex = 0; // se desplaza con teclado
    const dialogo = el(
      'div',
      'q-lector',
      el('header', 'q-lector__cabecera', el('div', '', el('p', 'q-lector__capitulo', `Capítulo ${n}`), encabezado), cerrarBoton),
      desplazable,
    );
    dialogo.dataset.testid = 'lector';
    dialogo.setAttribute('role', 'dialog');
    dialogo.setAttribute('aria-modal', 'true');
    dialogo.setAttribute('aria-labelledby', encabezado.id);
    capa.replaceChildren(dialogo);
    capa.hidden = false;
    cerrarBoton.focus();
  }

  capa.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') {
      evento.preventDefault();
      cerrar();
      return;
    }
    if (evento.key !== 'Tab') return;
    // El foco no sale del diálogo (VAL-18): Tab da la vuelta dentro de él.
    const focusables = [...capa.querySelectorAll<HTMLElement>(FOCUSABLES)];
    const [primero, ultimo] = [focusables[0], focusables.at(-1)];
    if (evento.shiftKey && document.activeElement === primero) {
      evento.preventDefault();
      ultimo?.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primero?.focus();
    }
  });
  capa.addEventListener('click', (evento) => {
    if (evento.target === capa) cerrar();
  });

  const recurso = (clave: string, pedir: (senal: AbortSignal) => Promise<void>): Recurso => ({
    clave,
    cada: CADA_DATOS,
    async pedir(senal) {
      await pedir(senal);
      pintar();
    },
  });

  pintarLector();

  return {
    titulo: 'Lectura',
    nodo: el(
      'div',
      'q-vista q-vista--lectura',
      cabecera,
      tarjetaLibro.raiz,
      el('div', 'q-lectura', tarjetaEscena.raiz, tarjetaLista.raiz),
      capa,
    ),
    recursos: [
      recurso('config', async (s) => void (datos.config = await api.config(slug, s))),
      recurso('escaleta', async (s) => void (datos.escaleta = await api.escaleta(slug, s))),
      recurso('checkpoint', async (s) => void (datos.checkpoint = await api.checkpoint(slug, s))),
      recurso('capitulos', async (s) => void (datos.capitulos = await api.capitulos(slug, s))),
      recurso('libro', async (s) => void (datos.libro = await api.libro(slug, s))),
    ],
    actualizar(ruta) {
      if (ruta.vista !== 'lectura') return false;
      abierto = ruta.capitulo ?? null;
      if (abierto !== null) seleccionar(abierto);
      pintarLector();
      return true;
    },
    desmontar() {
      montada = false;
      peticion?.control.abort();
      escena3d?.liberar();
    },
  };
}
