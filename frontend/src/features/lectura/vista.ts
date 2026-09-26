// Lectura (RF-24 a RF-31, spec 0015): la portada con su ilustración, el índice y la ficha de
// personajes y lugares, y el lector en un diálogo modal. La ruta lleva el capítulo abierto (RF-10):
// se abre desde el índice, la ficha o «Empezar a leer». Un capítulo solo se pide si está cerrado, y
// no antes de conocer el checkpoint (RF-27, D8, VAL-7).
import type { Ruta, Vista } from '../../app/rutas';
import * as api from '../../shared/api/cliente';
import { ErrorDeApi } from '../../shared/api/errores';
import { SUBGENEROS } from '../../shared/obra';
import { CADA_DATOS, type Recurso } from '../../shared/sondeo';
import { aviso, boton, el, esqueleto, vacio } from '../../shared/ui/componentes';
import { portada, tituloDe } from '../../shared/ui/portada';
import { estadosDeVolumen, type EstadoDeVolumen } from './estados';
import { libro } from './libro';

type E = api.Esquemas;

interface Datos {
  config?: E['Config'];
  checkpoint?: E['Checkpoint'] | null;
  capitulos?: E['FrontmatterCapitulo'][];
  libro?: E['Libro'];
}

const FOCUSABLES = 'button:not(:disabled), [href], [tabindex]:not([tabindex="-1"])';

type Tema = 'papel' | 'sepia' | 'noche';
const TEMAS: readonly Tema[] = ['papel', 'sepia', 'noche'];
const LETRA = { minima: 14, maxima: 26, paso: 2 } as const;
/** Fondo y tamaño de letra del lector: duran lo que la pestaña, sin guardarse en el navegador
 * (spec 0015, D9; RNF-09 de la spec 0004). */
const preferencias: { tema: Tema; tamano: number } = { tema: 'papel', tamano: 18 };

export function lectura({ slug, capitulo }: { slug: string; capitulo?: number }, navegar: (ruta: Ruta) => void): Vista {
  const datos: Datos = {};
  let abierto: number | null = capitulo ?? null;
  let texto: { n: number; nodo: HTMLElement } | { n: number; error: string } | null = null;
  let peticion: { n: number; control: AbortController } | null = null;
  /** El enlace que abrió el lector, para devolverle el foco al cerrarlo. */
  let origen: HTMLElement | null = null;

  const cubierta = portada({ slug, tamano: 'grande', decorativa: true });
  // Portada, índice y ficha (docs/lectura-web.md): se rehace solo si cambia el libro.
  const contenido = el('div', 'q-lectura', esqueleto('q-esqueleto--portada'), esqueleto('q-esqueleto--lista'));
  let libroPintado = '';
  const capa = el('div', 'q-lector-capa');
  capa.hidden = true;

  const estados = (): EstadoDeVolumen[] =>
    estadosDeVolumen(datos.config?.parametros_obra.num_capitulos ?? 0, datos.checkpoint ?? null, (datos.capitulos ?? []).map((c) => c.capitulo));
  const titulo = (n: number): string => datos.capitulos?.find((c) => c.capitulo === n)?.titulo ?? `Capítulo ${n}`;
  const abrir = (n: number): void => navegar({ vista: 'lectura', slug, capitulo: n });
  const cerrar = (): void => navegar({ vista: 'lectura', slug });

  contenido.addEventListener('click', (evento) => {
    const enlace = (evento.target as Element).closest('a');
    if (enlace) origen = enlace;
  });

  function pintar(): void {
    const obra = datos.config?.parametros_obra;
    const firmaDelLibro = JSON.stringify([datos.libro, obra?.subgenero, obra?.num_capitulos]);
    if (datos.libro && firmaDelLibro !== libroPintado) {
      libroPintado = firmaDelLibro;
      const subtitulo = obra ? `${SUBGENEROS[obra.subgenero]} · ${obra.num_capitulos} capítulos` : '';
      const conTitulo = { ...datos.libro, titulo: tituloDe(datos.libro, slug) };
      cubierta.poner(conTitulo.titulo, obra ? SUBGENEROS[obra.subgenero] : '');
      contenido.replaceChildren(libro(conTitulo, slug, cubierta.raiz, subtitulo));
    }
    if (datos.checkpoint === undefined || datos.capitulos === undefined || !datos.config) return;
    pintarLector();
  }

  async function pedirCapitulo(n: number): Promise<void> {
    const control = new AbortController();
    peticion = { n, control };
    try {
      // markdown-it y el lector llegan en el chunk de Lectura (RNF-02).
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
        if (origen?.isConnected) origen.focus();
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
    mostrarDialogo(n, cuerpo, fase);
  }

  /** La portada del libro abierto: la ilustración en la página izquierda y el título con la
   * dedicatoria en la derecha; el capítulo 1 empieza al pasar la página (spec 0015). */
  function portadaDelLibro(): HTMLElement {
    const obra = datos.config?.parametros_obra;
    const nombre = tituloDe(datos.libro, slug);
    const genero = obra ? SUBGENEROS[obra.subgenero] : '';
    const cubierta = portada({ slug, tamano: 'grande', decorativa: true });
    cubierta.poner(nombre, genero);
    const dedicatoria = datos.libro?.dedicatoria;
    const seccion = el(
      'section',
      'q-lector__portada',
      el('div', 'q-lector__hoja q-lector__hoja--cubierta', cubierta.raiz),
      el(
        'div',
        'q-lector__hoja q-lector__hoja--titulo',
        ...(genero ? [el('p', 'q-lector__portada-genero', genero)] : []),
        el('p', 'q-lector__portada-titulo', nombre),
        ...(dedicatoria ? [el('p', 'q-lector__portada-dedicatoria', dedicatoria)] : []),
        el('p', 'q-lector__portada-pie', 'Pasa la página para empezar'),
      ),
    );
    seccion.setAttribute('aria-label', 'Portada');
    return seccion;
  }

  let firma = '';
  /** Las teclas del lector abierto: ← → cambian de capítulo, AvPág y RePág pasan página. */
  let teclas: Record<string, () => void> = {};
  /** Al retroceder desde el primer pliego, el anterior se abre por su último pliego. */
  let volverAlFinal = false;
  const irA = (n: number, alFinal = false): void => {
    volverAlFinal = alFinal;
    abrir(n);
  };

  function mostrarDialogo(n: number, cuerpo: HTMLElement, fase: string): void {
    const encabezado = el('h2', 'q-lector__titulo');
    encabezado.id = 'q-lector-titulo';
    encabezado.dataset.testid = 'lector-titulo';
    encabezado.textContent = titulo(n); // el título lo escribe un agente: siempre como texto (D56)
    const cerrarBoton = boton('Cerrar', { variante: 'secundario' });
    cerrarBoton.addEventListener('click', cerrar);
    const anterior = n > 1 ? n - 1 : null;
    const siguiente = estados()[n] === 'cerrado' ? n + 1 : null;
    const flecha = (destino: number | null, nombre: string, simbolo: string): HTMLElement[] => {
      if (destino === null) return [];
      const b = boton(simbolo, { variante: 'secundario' });
      b.setAttribute('aria-label', nombre);
      b.title = `${nombre}: ${titulo(destino)}`;
      b.addEventListener('click', () => irA(destino));
      return [b];
    };

    // Libro abierto: el texto va en columnas de una página y cada pliego (dos páginas, una en
    // pantalla estrecha) se muestra desplazándolo su propio ancho más el hueco (app.css).
    if (n === 1 && fase === 'texto' && !cuerpo.querySelector('.q-lector__portada') && cuerpo.classList.contains('q-lector__texto')) {
      cuerpo.prepend(portadaDelLibro());
    }
    const hojas = el('div', 'q-lector__cuerpo', cuerpo);
    let pliego = 0;
    const pliegos = (): number => {
      if (!cuerpo.clientWidth) return 1;
      const hueco = parseFloat(getComputedStyle(cuerpo).columnGap) || 0;
      return Math.max(1, Math.ceil((cuerpo.scrollWidth + hueco) / (cuerpo.clientWidth + hueco) - 0.01));
    };
    const irAPliego = (p: number): void => {
      pliego = p;
      cuerpo.style.setProperty('--pliego', String(p));
      hojas.dataset.pliego = String(p);
    };
    const pasar = (delta: 1 | -1): void => {
      const cuantos = pliegos();
      const p = Math.min(pliego, cuantos - 1) + delta;
      if (p >= cuantos) {
        if (siguiente !== null) irA(siguiente);
      } else if (p < 0) {
        if (anterior !== null) irA(anterior, true);
      } else irAPliego(p);
    };
    const pasador = (lado: 'anterior' | 'siguiente', delta: 1 | -1): HTMLButtonElement => {
      const b = el('button', `q-lector__pasar q-lector__pasar--${lado}`);
      b.type = 'button';
      b.setAttribute('aria-label', `Página ${lado}`);
      b.addEventListener('click', () => pasar(delta));
      return b;
    };
    hojas.append(pasador('anterior', -1), pasador('siguiente', 1));
    irAPliego(0);
    teclas = {
      ArrowLeft: () => anterior !== null && irA(anterior),
      ArrowRight: () => siguiente !== null && irA(siguiente),
      PageUp: () => pasar(-1),
      PageDown: () => pasar(1),
    };

    // Fondo y letra: se aplican al diálogo y, si cambia la letra, se recoloca el pliego.
    const temas = el(
      'div',
      'q-lector__temas',
      ...TEMAS.map((t) => {
        const b = el('button', `q-lector__tema q-lector__tema--${t}`);
        b.type = 'button';
        b.dataset.tema = t;
        b.setAttribute('aria-label', `Fondo ${t}`);
        b.title = `Fondo ${t}`;
        b.addEventListener('click', () => {
          preferencias.tema = t;
          aplicar();
        });
        return b;
      }),
    );
    temas.setAttribute('role', 'group');
    temas.setAttribute('aria-label', 'Color del fondo');
    const letra = (texto: string, nombre: string, delta: number): HTMLButtonElement => {
      const b = boton(texto, { variante: 'secundario' });
      b.classList.add('q-lector__letra');
      b.setAttribute('aria-label', nombre);
      b.title = nombre;
      b.addEventListener('click', () => {
        preferencias.tamano = Math.min(LETRA.maxima, Math.max(LETRA.minima, preferencias.tamano + delta));
        aplicar();
      });
      return b;
    };
    const menos = letra('A−', 'Reducir letra', -LETRA.paso);
    const mas = letra('A+', 'Aumentar letra', LETRA.paso);

    const dialogo = el(
      'div',
      'q-lector',
      el(
        'header',
        'q-lector__cabecera',
        el('div', '', el('p', 'q-lector__capitulo', `Capítulo ${n}`), encabezado),
        el(
          'div',
          'q-lector__acciones',
          temas,
          el('div', 'q-lector__grupo', menos, mas),
          el('div', 'q-lector__grupo', ...flecha(anterior, 'Capítulo anterior', '←'), ...flecha(siguiente, 'Capítulo siguiente', '→')),
          cerrarBoton,
        ),
      ),
      hojas,
    );
    function aplicar(): void {
      // Una hoja de la portada ocupa una página: en columnas, su altura en % no se resuelve.
      if (cuerpo.clientHeight) cuerpo.style.setProperty('--alto-pagina', `${cuerpo.clientHeight}px`);
      dialogo.dataset.tema = preferencias.tema;
      dialogo.style.setProperty('--tamano-lectura', `${preferencias.tamano}px`);
      for (const b of temas.querySelectorAll<HTMLButtonElement>('button')) b.setAttribute('aria-pressed', String(b.dataset.tema === preferencias.tema));
      menos.disabled = preferencias.tamano <= LETRA.minima;
      mas.disabled = preferencias.tamano >= LETRA.maxima;
      irAPliego(Math.min(pliego, pliegos() - 1));
    }
    aplicar();
    dialogo.dataset.testid = 'lector';
    dialogo.setAttribute('role', 'dialog');
    dialogo.setAttribute('aria-modal', 'true');
    dialogo.setAttribute('aria-labelledby', encabezado.id);
    capa.replaceChildren(dialogo);
    capa.hidden = false;
    aplicar(); // ya en el documento, con medidas
    cerrarBoton.focus();
    if (volverAlFinal && fase === 'texto') {
      volverAlFinal = false;
      cuerpo.style.transition = 'none'; // sin recorrer el capítulo entero hasta su último pliego
      irAPliego(pliegos() - 1);
      void cuerpo.offsetWidth;
      cuerpo.style.transition = '';
    }
  }

  capa.addEventListener('keydown', (evento) => {
    const accion = teclas[evento.key];
    if (accion) {
      evento.preventDefault();
      accion();
      return;
    }
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
    nodo: el('div', 'q-vista q-vista--lectura', contenido, capa),
    recursos: [
      recurso('config', async (s) => void (datos.config = await api.config(slug, s))),
      recurso('checkpoint', async (s) => void (datos.checkpoint = await api.checkpoint(slug, s))),
      recurso('capitulos', async (s) => void (datos.capitulos = await api.capitulos(slug, s))),
      recurso('libro', async (s) => void (datos.libro = await api.libro(slug, s))),
    ],
    actualizar(ruta) {
      if (ruta.vista !== 'lectura') return false;
      abierto = ruta.capitulo ?? null;
      pintarLector();
      return true;
    },
    desmontar() {
      peticion?.control.abort();
    },
  };
}
