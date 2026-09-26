// La conversación de Lanzar (spec 0015, RF-09): una pregunta cada vez, en el orden de PASOS, y
// cada respuesta validada con las reglas de validacion.ts antes de pasar a la siguiente. Puro: la
// vista pinta las burbujas y esto decide qué se pregunta y qué se guarda.
import { comprobarSlug, GENEROS, TONOS, validar, type Campos } from './validacion';

export type Paso = keyof Campos | 'regalo';

export interface Opcion {
  valor: string;
  rotulo: string;
}

export interface Pregunta {
  paso: Paso;
  texto: string;
  opciones: Opcion[];
  omitible: boolean;
  multilinea: boolean;
}

export interface Conversacion {
  campos: Campos;
  regalo: boolean;
  paso: Paso | 'resumen';
}

const PASOS: Paso[] = ['regalo', 'nombre', 'edad', 'rasgos', 'recuerdos', 'idea', 'genero', 'tono', 'capitulos', 'palabras', 'slug'];
const DEL_REGALO: Paso[] = ['nombre', 'edad', 'rasgos', 'recuerdos'];

const opciones = (o: Record<string, string>): Opcion[] => Object.entries(o).map(([valor, rotulo]) => ({ valor, rotulo }));
const numeros = (...n: number[]): Opcion[] => n.map((v) => ({ valor: String(v), rotulo: v.toLocaleString('es-ES') }));

export function inicial(): Conversacion {
  const campos: Campos = { slug: '', idea: '', capitulos: '', palabras: '', nombre: '', edad: '', rasgos: '', recuerdos: '', genero: '', tono: '' };
  return { campos, regalo: false, paso: 'regalo' };
}

function siguiente(c: Conversacion): Paso | 'resumen' {
  const resto = PASOS.slice(PASOS.indexOf(c.paso as Paso) + 1).filter((p) => c.regalo || !DEL_REGALO.includes(p));
  return resto[0] ?? 'resumen';
}

export function pregunta(c: Conversacion, existentes: readonly string[] = []): Pregunta | null {
  const p = (texto: string, extra: Partial<Pregunta> = {}): Pregunta => ({
    paso: c.paso as Paso,
    texto,
    opciones: [],
    omitible: false,
    multilinea: false,
    ...extra,
  });
  switch (c.paso) {
    case 'regalo':
      return p('Hola. Vamos a escribir una novela de suspense. ¿Es un regalo para alguien?', {
        opciones: [
          { valor: 'si', rotulo: 'Sí, es un regalo' },
          { valor: 'no', rotulo: 'No, es para mí' },
        ],
      });
    case 'nombre':
      return p('¡Qué bonito! ¿Cómo se llama la persona que la va a recibir?');
    case 'edad':
      return p('¿Qué edad tiene?', { omitible: true });
    case 'rasgos':
      return p('Cuéntame cómo es: algunos rasgos de su forma de ser, uno por línea.', { omitible: true, multilinea: true });
    case 'recuerdos':
      return p('¿Hay algún recuerdo compartido que te gustaría que apareciera? Uno por línea.', { omitible: true, multilinea: true });
    case 'idea':
      return c.regalo
        ? p('¿Tienes alguna idea para la trama? Si no, la construyo con lo que me has contado.', { omitible: true, multilinea: true })
        : p('¿Qué historia te gustaría contar? Descríbeme la idea en unas líneas.', { multilinea: true });
    case 'genero':
      return p('¿Qué tipo de suspense te apetece?', { opciones: opciones(GENEROS), omitible: true });
    case 'tono':
      return p('¿Y el tono?', { opciones: opciones(TONOS), omitible: true });
    case 'capitulos':
      return p('¿Cuántos capítulos quieres que tenga?', { opciones: numeros(6, 10, 16, 24) });
    case 'palabras':
      return p('¿Cuántas palabras en total, más o menos?', { opciones: numeros(15000, 30000, 60000, 80000) });
    case 'slug': {
      const sugerido = sugerirSlug(c.campos.idea || (c.campos.nombre && `para ${c.campos.nombre}`), existentes);
      return p('Por último, dale un nombre corto para encontrarla: minúsculas, números y guiones.', {
        opciones: [{ valor: sugerido, rotulo: sugerido }],
      });
    }
    case 'resumen':
      return null;
  }
}

/** Lo que dice el asistente cuando validar rechaza una respuesta: el motivo, sin la regex. */
const EN_CHARLA: Partial<Record<keyof Campos, string>> = {
  capitulos: 'necesito un número entero de capítulos, entre 1 y 999',
  palabras: 'necesito un número entero de palabras, por ejemplo 30.000',
  edad: 'necesito una edad en números, entre 0 y 120',
  slug: 'el nombre corto solo admite minúsculas sin tildes, números y guiones',
};

/** «80.000» o «80 000» como 80000; cualquier otra cosa, tal cual, para que validar la rechace. */
const sinMiles = (v: string): string => (/^\d{1,3}([.\s]\d{3})+$/.test(v) ? v.replace(/[.\s]/g, '') : v);

export function responder(
  c: Conversacion,
  valor: string,
  existentes: readonly string[] | null,
): { conversacion: Conversacion; error?: string } {
  const actual = pregunta(c, existentes ?? []);
  if (!actual) return { conversacion: c };
  if (c.paso === 'regalo') {
    if (valor !== 'si' && valor !== 'no') return { conversacion: c, error: 'elige una de las dos opciones' };
    const nueva = { ...c, regalo: valor === 'si' };
    return { conversacion: { ...nueva, paso: siguiente(nueva) } };
  }
  const paso = c.paso as keyof Campos;
  const texto = paso === 'capitulos' || paso === 'palabras' ? sinMiles(valor.trim()) : valor;
  if (!/\S/.test(texto) && !actual.omitible) return { conversacion: c, error: 'necesito una respuesta para seguir' };
  const campos = { ...c.campos, [paso]: /\S/.test(texto) ? texto : '' };
  const invalido = validar(campos)[paso];
  if (invalido) return { conversacion: c, error: EN_CHARLA[paso] ?? invalido };
  if (paso === 'slug' && comprobarSlug(campos.slug, existentes).error) {
    return { conversacion: c, error: `ya existe una novela llamada ${campos.slug}; elige otro nombre` };
  }
  const nueva = { ...c, campos };
  return { conversacion: { ...nueva, paso: siguiente(nueva) } };
}

export function resumen({ campos: c }: Conversacion): [string, string][] {
  const rotulo = (o: Record<string, string>, v: string): string => (Object.hasOwn(o, v) ? o[v]! : v);
  const filas: [string, string][] = [
    ['Para', [c.nombre.trim(), c.edad && `${c.edad} años`].filter(Boolean).join(', ')],
    ['Rasgos', c.rasgos.trim()],
    ['Recuerdos', c.recuerdos.trim()],
    ['Idea', c.idea.trim()],
    ['Género', rotulo(GENEROS, c.genero)],
    ['Tono', rotulo(TONOS, c.tono)],
    ['Capítulos', c.capitulos],
    ['Palabras', c.palabras && Number(c.palabras).toLocaleString('es-ES')],
    ['Nombre corto', c.slug],
  ];
  return filas.filter(([, v]) => v);
}

const VACIAS = new Set('a al con de del el en la las lo los para por que se su sus un una unas unos y'.split(' '));

/** Las cuatro primeras palabras con contenido de `texto`, en forma de slug y con sufijo si ya existe. */
export function sugerirSlug(texto: string, existentes: readonly string[]): string {
  const base =
    texto
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((p) => p && !VACIAS.has(p))
      .slice(0, 4)
      .join('-') || 'novela-nueva';
  let slug = base;
  for (let n = 2; existentes.includes(slug); n++) slug = `${base}-${n}`;
  return slug;
}
