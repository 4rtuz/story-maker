// La portada de una novela (spec 0015, §5.5): la ilustración de `novela portada` con el título
// encima, como una cubierta de verdad. Si la imagen no existe o no carga, queda la cubierta
// tipográfica con los colores de la marca. El título entra como texto (D56).
import { urlDePortada } from '../api/cliente';
import { el } from './componentes';

export interface Portada {
  raiz: HTMLElement;
  /** Cambia título y subtítulo sin volver a pedir la imagen. */
  poner(titulo: string, subtitulo?: string): void;
}

/** El título mientras no llega el del libro: el slug con espacios. */
export const tituloProvisional = (slug: string): string => {
  const texto = slug.replaceAll('-', ' ');
  return `${texto[0]?.toUpperCase() ?? ''}${texto.slice(1)}`;
};

/** El título del libro, o el provisional si el libro todavía no lo tiene: hoy la API sirve el slug
 * como título mientras la novela no tenga uno propio. */
export const tituloDe = (libro: { titulo: string } | null | undefined, slug: string): string =>
  libro && libro.titulo !== slug ? libro.titulo : tituloProvisional(slug);

export function portada({
  slug,
  tamano = 'normal',
  decorativa = false,
}: {
  slug: string;
  tamano?: 'mini' | 'normal' | 'grande';
  /** Oculta a los lectores de pantalla cuando el título ya está al lado como encabezado. */
  decorativa?: boolean;
}): Portada {
  const titulo = el('span', 'q-portada__titulo', tituloProvisional(slug));
  const subtitulo = el('span', 'q-portada__subtitulo');
  const imagen = el('img', 'q-portada__imagen');
  imagen.alt = '';
  imagen.decoding = 'async';
  imagen.loading = tamano === 'grande' ? 'eager' : 'lazy';
  const raiz = el('div', `q-portada q-portada--${tamano}`, imagen, el('span', 'q-portada__rotulo', subtitulo, titulo));
  imagen.addEventListener('load', () => raiz.classList.add('q-portada--cargada'), { once: true });
  imagen.addEventListener(
    'error',
    () => {
      imagen.remove();
      raiz.classList.add('q-portada--tipografica');
    },
    { once: true },
  );
  imagen.src = urlDePortada(slug);
  if (decorativa) raiz.setAttribute('aria-hidden', 'true');
  return {
    raiz,
    poner(t, s = '') {
      if (titulo.textContent !== t) titulo.textContent = t;
      if (subtitulo.textContent !== s) subtitulo.textContent = s;
    },
  };
}
