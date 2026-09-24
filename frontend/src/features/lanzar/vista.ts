// Lanzar (RF-11 a RF-16): el formulario prepara la orden /novela-nueva y las de la sesión del
// harness para copiarlas. No escribe ficheros ni pide a la API nada más que GET /novelas (D5).
import type { Vista } from '../../app/rutas';
import * as api from '../../shared/api/cliente';
import { CADA_DATOS } from '../../shared/sondeo';
import { boton, campo, el, esqueleto, estadoVacio, etiqueta, tarjeta, type Campo } from '../../shared/ui/componentes';
import { ordenesDeSesion, ordenNovelaNueva } from './orden';
import { comprobarSlug, validar, type Campos } from './validacion';

/** Un bloque de órdenes en monoespaciada con su botón «Copiar» y la alternativa de RF-11. */
function bloqueDeOrden(titulo: string, detalle: string) {
  const texto = el('pre', 'q-orden__texto');
  const estado = el('p', 'q-orden__estado');
  estado.setAttribute('role', 'status');
  const copiar = boton('Copiar', { variante: 'secundario', icono: 'copy', deshabilitado: true });
  copiar.append(el('span', 'q-oculto-visual', ` ${detalle}`));
  const raiz = el(
    'div',
    'q-orden',
    el('div', 'q-orden__cabecera', el('h3', 'q-orden__titulo', titulo), copiar),
    texto,
    estado,
  );

  copiar.addEventListener('click', async () => {
    const valor = texto.textContent ?? '';
    raiz.querySelector('.q-orden__manual')?.remove();
    try {
      await navigator.clipboard.writeText(valor);
      estado.textContent = 'copiada al portapapeles';
    } catch {
      // Sin portapapeles, o denegado: el texto seleccionado en un campo de solo lectura.
      const manual = el('textarea', 'q-campo__control q-orden__manual');
      manual.readOnly = true;
      manual.value = valor;
      manual.rows = Math.min(8, valor.split('\n').length + 1);
      manual.setAttribute('aria-label', `${titulo}, para copiar`);
      raiz.insertBefore(manual, estado);
      manual.focus();
      manual.setSelectionRange(0, valor.length);
      estado.textContent = 'pulsa Ctrl+C para copiar';
    }
  });

  return {
    raiz,
    poner(valor: string) {
      texto.textContent = valor;
      copiar.disabled = !valor;
      estado.textContent = '';
      raiz.querySelector('.q-orden__manual')?.remove();
    },
  };
}

export function lanzar(): Vista {
  const campos = {
    slug: campo({ id: 'lanzar-slug', etiqueta: 'Slug' }),
    idea: campo({ id: 'lanzar-idea', etiqueta: 'Idea', multilinea: true }),
    capitulos: campo({ id: 'lanzar-capitulos', etiqueta: 'Capítulos (opcional)', modoTeclado: 'numeric' }),
    palabras: campo({ id: 'lanzar-palabras', etiqueta: 'Palabras totales (opcional)', modoTeclado: 'numeric' }),
  } satisfies Record<keyof Campos, Campo>;
  campos.slug.control.setAttribute('autocomplete', 'off');
  let existentes: string[] | null = null;

  const orden = bloqueDeOrden('Orden', 'la orden de /novela-nueva');
  const sesion = bloqueDeOrden('Sesión del harness', 'las órdenes de la sesión del harness');
  const aviso = el('p', 'q-lanzar__aviso');
  aviso.hidden = true;
  // Aparte y a todo el ancho: las órdenes caben en una línea y no se parten dentro de un flag.
  const salida = tarjeta({ titulo: 'Órdenes para copiar', icono: 'terminal', tono: 'cian', clase: 'q-lanzar__salida' });
  salida.cuerpo.classList.add('q-lanzar__resultado');
  salida.cuerpo.append(aviso, orden.raiz, sesion.raiz);
  salida.raiz.hidden = true;

  const generar = boton('Generar orden', { icono: 'rocket' });
  generar.addEventListener('click', () => {
    const valores: Campos = {
      slug: campos.slug.control.value,
      idea: campos.idea.control.value,
      capitulos: campos.capitulos.control.value,
      palabras: campos.palabras.control.value,
    };
    const errores = validar(valores);
    const slug = errores.slug ? {} : comprobarSlug(valores.slug, existentes);
    if (slug.error) errores.slug = slug.error;
    for (const [clave, c] of Object.entries(campos)) c.mostrarError(errores[clave as keyof Campos] ?? null);
    const valido = Object.keys(errores).length === 0;
    orden.poner(valido ? ordenNovelaNueva(valores) : '');
    sesion.poner(valido ? ordenesDeSesion(valores.slug).join('\n') : '');
    aviso.textContent = slug.aviso ?? '';
    aviso.hidden = !valido || !slug.aviso;
    salida.raiz.hidden = !valido;
    if (!valido) {
      const primero = (Object.keys(campos) as (keyof Campos)[]).find((c) => errores[c]);
      if (primero) campos[primero].control.focus();
    }
  });

  const formulario = tarjeta({ titulo: 'Nueva novela', icono: 'rocket', tono: 'naranja', clase: 'q-lanzar__formulario' });
  formulario.cuerpo.append(
    el('div', 'q-lanzar__campos', campos.slug.raiz, campos.idea.raiz, el('div', 'q-lanzar__numeros', campos.capitulos.raiz, campos.palabras.raiz)),
    el('div', 'q-lanzar__acciones', generar),
  );

  const lista = tarjeta({ titulo: 'Slugs en uso', icono: 'library', tono: 'cian', clase: 'q-lanzar__slugs' });
  lista.cuerpo.append(esqueleto('q-esqueleto--slugs'));

  return {
    titulo: 'Lanzar',
    nodo: el('div', 'q-vista q-vista--lanzar', formulario.raiz, lista.raiz, salida.raiz),
    recursos: [
      {
        clave: 'novelas',
        cada: CADA_DATOS,
        async pedir(senal) {
          try {
            existentes = (await api.novelas(senal)).map((n) => n.slug);
          } catch (error) {
            existentes = null; // no ha respondido o ha fallado: la orden sale con el aviso (D43)
            throw error;
          }
          lista.contar(existentes.length);
          lista.cuerpo.replaceChildren(
            existentes.length
              ? el('div', 'q-lanzar__etiquetas', ...existentes.map(etiqueta))
              : estadoVacio({
                  icono: 'library',
                  texto: 'todavía no hay novelas: lanza la primera',
                  pista: 'Un slug nuevo no puede coincidir con ninguno de esta lista.',
                }),
          );
        },
      },
    ],
  };
}
