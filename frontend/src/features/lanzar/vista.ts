// Lanzar: el formulario lanza la novela en el backend (POST /lanzamientos), que la escribe de
// principio a fin con `novela producir`. No hay órdenes que copiar. Debajo, cada lanzamiento con su
// paso, su motivo y las últimas líneas de sus sesiones, y los botones para detenerlo o reanudarlo.
import type { Vista } from '../../app/rutas';
import * as api from '../../shared/api/cliente';
import type { Esquemas } from '../../shared/api/cliente';
import { ErrorDeApi } from '../../shared/api/errores';
import { CADA_DATOS, CADA_LOG } from '../../shared/sondeo';
import { boton, campo, el, esqueleto, estadoVacio, etiqueta, tarjeta, vacio, type Campo } from '../../shared/ui/componentes';
import { comprobarSlug, validar, type Campos } from './validacion';

type Fila = Esquemas['Lanzamiento'];

const ESTADOS: Record<Fila['estado'], string> = {
  en_marcha: 'en marcha',
  terminado: 'terminada',
  fallido: 'fallida',
  detenido: 'detenida',
  interrumpido: 'interrumpida',
};

const motivo = (error: unknown): string => (error instanceof ErrorDeApi ? error.detalle : String(error));

export function lanzar(): Vista {
  const campos = {
    slug: campo({ id: 'lanzar-slug', etiqueta: 'Slug' }),
    idea: campo({ id: 'lanzar-idea', etiqueta: 'Idea', multilinea: true }),
    capitulos: campo({ id: 'lanzar-capitulos', etiqueta: 'Capítulos (opcional)', modoTeclado: 'numeric' }),
    palabras: campo({ id: 'lanzar-palabras', etiqueta: 'Palabras totales (opcional)', modoTeclado: 'numeric' }),
  } satisfies Record<keyof Campos, Campo>;
  campos.slug.control.setAttribute('autocomplete', 'off');
  let existentes: string[] | null = null;
  let actuales: Fila[] = [];

  const envio = el('p', 'q-lanzar__aviso q-lanzar__resultado-envio');
  envio.setAttribute('role', 'status');
  envio.hidden = true;
  const avisar = (texto: string): void => {
    envio.textContent = texto;
    envio.hidden = !texto;
  };

  const lista = tarjeta({ titulo: 'Lanzamientos', icono: 'terminal', tono: 'cian', clase: 'q-lanzar__salida' });
  lista.cuerpo.classList.add('q-lanzar__resultado');
  lista.cuerpo.append(esqueleto('q-esqueleto--slugs'));

  /** Una petición de un botón: deshabilitado mientras dura, y su resultado en la lista al volver. */
  async function accion(b: HTMLButtonElement, pedir: () => Promise<Fila>, exito: string): Promise<void> {
    b.disabled = true;
    try {
      const nuevo = await pedir();
      pintar([nuevo, ...actuales.filter((l) => l.slug !== nuevo.slug)]);
      avisar(exito);
    } catch (error) {
      avisar(motivo(error));
    } finally {
      b.disabled = false;
    }
  }

  function fila(l: Fila): HTMLElement {
    const acciones = el('div', 'q-lanzamiento__acciones');
    if (l.estado === 'en_marcha' && !l.detener_pedido) {
      const b = boton('Detener', { variante: 'secundario' });
      b.append(el('span', 'q-oculto-visual', ` ${l.slug}`));
      b.addEventListener('click', () => void accion(b, () => api.detener(l.slug), `${l.slug}: se detendrá tras el capítulo en curso`));
      acciones.append(b);
    } else if (l.estado !== 'en_marcha' && l.estado !== 'terminado') {
      const b = boton('Reanudar', { variante: 'secundario', icono: 'rocket' });
      b.append(el('span', 'q-oculto-visual', ` ${l.slug}`));
      b.addEventListener('click', () => void accion(b, () => api.reanudar(l.slug), `${l.slug}: reanudada`));
      acciones.append(b);
    }
    const estado = l.detener_pedido && l.estado === 'en_marcha' ? 'en marcha · se detendrá tras el capítulo en curso' : ESTADOS[l.estado];
    const registro = el('pre', 'q-lanzamiento__registro', (l.registro ?? []).join('\n'));
    registro.hidden = !l.registro?.length;
    return el(
      'article',
      `q-lanzamiento q-lanzamiento--${l.estado}`,
      el('div', 'q-lanzamiento__cabecera', el('h3', 'q-lanzamiento__titulo', l.slug), etiqueta(estado), acciones),
      el('p', 'q-lanzamiento__detalle', `${l.paso} · ${l.detalle}`),
      registro,
    );
  }

  function pintar(lanzamientos: Fila[]): void {
    actuales = lanzamientos;
    lista.contar(lanzamientos.length);
    lista.cuerpo.replaceChildren(
      envio,
      ...(lanzamientos.length ? lanzamientos.map(fila) : [vacio('todavía no se ha lanzado ninguna novela desde el panel')]),
    );
  }

  const lanzarBoton = boton('Lanzar novela', { icono: 'rocket' });
  lanzarBoton.addEventListener('click', () => {
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
    const primero = (Object.keys(campos) as (keyof Campos)[]).find((c) => errores[c]);
    if (primero) {
      campos[primero].control.focus();
      return;
    }
    const peticion: Esquemas['PeticionDeLanzamiento'] = { slug: valores.slug, idea: valores.idea };
    if (valores.capitulos) peticion.capitulos = Number(valores.capitulos);
    if (valores.palabras) peticion.palabras = Number(valores.palabras);
    void accion(lanzarBoton, () => api.lanzar(peticion), `${valores.slug}: lanzada; el backend la escribe de principio a fin`);
  });

  const formulario = tarjeta({ titulo: 'Nueva novela', icono: 'rocket', tono: 'naranja', clase: 'q-lanzar__formulario' });
  formulario.cuerpo.append(
    el('div', 'q-lanzar__campos', campos.slug.raiz, campos.idea.raiz, el('div', 'q-lanzar__numeros', campos.capitulos.raiz, campos.palabras.raiz)),
    el('div', 'q-lanzar__acciones', lanzarBoton),
  );

  const slugs = tarjeta({ titulo: 'Slugs en uso', icono: 'library', tono: 'cian', clase: 'q-lanzar__slugs' });
  slugs.cuerpo.append(esqueleto('q-esqueleto--slugs'));

  return {
    titulo: 'Lanzar',
    nodo: el('div', 'q-vista q-vista--lanzar', formulario.raiz, slugs.raiz, lista.raiz),
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
          slugs.contar(existentes.length);
          slugs.cuerpo.replaceChildren(
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
      {
        clave: 'lanzamientos',
        cada: CADA_LOG,
        async pedir(senal) {
          const texto = envio.textContent ?? '';
          pintar(await api.lanzamientos(senal));
          avisar(texto);
        },
      },
    ],
  };
}
