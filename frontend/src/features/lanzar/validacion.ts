// Validación de Lanzar (RF-12, RF-13; D41 a D43). Ningún valor se normaliza: lo que no casa es un
// error con su motivo, y la orden solo lleva lo que el operador escribió.

export interface Campos {
  slug: string;
  idea: string;
  capitulos: string;
  palabras: string;
}

export type Errores = Partial<Record<keyof Campos, string>>;

const SLUG = /^[a-z0-9-]+$/;
const CAPITULOS = /^[1-9][0-9]{0,2}$/;
const PALABRAS = /^[1-9][0-9]*$/;

export function validar({ slug, idea, capitulos, palabras }: Campos): Errores {
  const errores: Errores = {};
  if (!SLUG.test(slug)) {
    errores.slug = slug ? 'solo minúsculas sin tilde, dígitos y guiones: ^[a-z0-9-]+$' : 'falta el slug';
  }
  if (!/\S/.test(idea)) errores.idea = 'la idea no puede estar vacía ni ser solo espacios';
  if (capitulos && !CAPITULOS.test(capitulos)) {
    errores.capitulos = 'un entero de 1 a 999, solo dígitos, sin ceros a la izquierda, signo ni espacios';
  }
  if (palabras && !PALABRAS.test(palabras)) {
    errores.palabras = 'un entero positivo, solo dígitos, sin ceros a la izquierda, signo ni espacios';
  }
  return errores;
}

/** El slug contra la lista de GET /novelas, o null si esa lista no ha llegado o ha fallado. */
export function comprobarSlug(slug: string, existentes: readonly string[] | null): { error?: string; aviso?: string } {
  if (existentes === null) return { aviso: 'no se ha podido comprobar si el slug ya existe' };
  if (existentes.includes(slug)) {
    return { error: `ya existe una novela ${slug}: novela nueva saldrá con 1 sin tocar nada` };
  }
  return {};
}
