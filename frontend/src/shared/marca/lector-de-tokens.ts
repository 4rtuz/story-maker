// Los colores de tokens.css para lo que no puede escribir var(): los materiales de Three.js y los
// atributos del SVG de la gráfica (RF-55). Dos implementaciones con la misma salida: el navegador
// resuelve el rol en un elemento, y los tests leen tokens.css como texto (VER-19).

export interface Rgba {
  r: number;
  g: number;
  b: number;
  a: number;
}

export type LectorDeTokens = (rol: string) => Rgba;

/** `#rrggbb`, sin el alfa: la escena y la gráfica solo leen roles opacos. */
export function hex({ r, g, b }: Rgba): string {
  return '#' + [r, g, b].map((c) => Math.round(c).toString(16).padStart(2, '0')).join('');
}

/** El color computado de una sonda pintada con el rol: el navegador resuelve var() y color-mix(). */
export function lectorDelNavegador(raiz: HTMLElement = document.body): LectorDeTokens {
  return (rol) => {
    const sonda = document.createElement('span');
    sonda.style.color = `var(${rol})`;
    raiz.append(sonda);
    const computado = getComputedStyle(sonda).color;
    sonda.remove();
    // Canales de 0 a 255 en la forma rgb, o de 0 a 1 en la forma color(srgb …) de color-mix().
    const escala = computado.startsWith('color(') ? 255 : 1;
    const [r = 0, g = 0, b = 0, a = 1] = (computado.match(/[\d.]+/g) ?? []).map(Number);
    return { r: r * escala, g: g * escala, b: b * escala, a };
  };
}

/** tokens.css como texto: sigue las cadenas de var() y entiende `color-mix(… N%, transparent)`. */
export function lectorDeCss(css: string): LectorDeTokens {
  const valores = new Map<string, string>();
  for (const [, nombre = '', valor = ''] of css.matchAll(/(--q-[\w-]+)\s*:\s*([^;]+);/g)) {
    valores.set(nombre, valor.trim());
  }
  const resolver = (valor: string): Rgba => {
    const referencia = valor.match(/^var\((--q-[\w-]+)\)$/)?.[1];
    if (referencia) return leer(referencia);
    const mezcla = valor.match(/^color-mix\(in srgb,\s*(.+?)\s+([\d.]+)%,\s*transparent\)$/);
    if (mezcla) {
      const color = resolver(mezcla[1] ?? '');
      return { ...color, a: (color.a * Number(mezcla[2])) / 100 };
    }
    const cifras = valor.match(/^#([0-9a-f]{6})$/i)?.[1];
    if (!cifras) throw new Error(`${valor}: no es un color que entienda el lector de tokens`);
    const n = Number.parseInt(cifras, 16);
    return { r: n >> 16, g: (n >> 8) & 255, b: n & 255, a: 1 };
  };
  const leer = (rol: string): Rgba => {
    const valor = valores.get(rol);
    if (valor === undefined) throw new Error(`${rol} no está en tokens.css`);
    return resolver(valor);
  };
  return leer;
}
