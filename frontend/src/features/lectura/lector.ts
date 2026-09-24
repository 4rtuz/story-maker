// El cuerpo de un capítulo en el lector (RF-25, RF-26; D14, D16, D56). Es el único módulo del
// panel que inserta HTML, y lo hace en una sola sentencia, con la salida de markdown-it: sin HTML
// del texto, sin enlaces, imágenes, autoenlaces ni referencias, y sin convertir URL sueltas, de
// modo que todo eso queda como texto. El título del capítulo no pasa por aquí: va con textContent.
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({ html: false, linkify: false }).disable(['link', 'image', 'autolink', 'reference']);

/** Si el texto empieza por una línea `---`, quita hasta la siguiente `---` inclusive. Acepta CRLF
 * y no es voraz: una regla horizontal del cuerpo se queda (VAL-16). */
export function quitarFrontmatter(texto: string): string {
  const lineas = texto.split('\n');
  if (lineas[0]?.trimEnd() !== '---') return texto;
  const cierre = lineas.findIndex((l, i) => i > 0 && l.trimEnd() === '---');
  return cierre === -1 ? texto : lineas.slice(cierre + 1).join('\n');
}

export function cuerpoDeCapitulo(markdown: string): HTMLElement {
  const contenedor = document.createElement('div');
  contenedor.className = 'q-lector__texto';
  // eslint-disable-next-line no-unsanitized/property
  contenedor.innerHTML = md.render(quitarFrontmatter(markdown));
  return contenedor;
}
