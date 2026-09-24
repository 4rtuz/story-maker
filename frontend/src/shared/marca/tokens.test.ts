// @vitest-environment node
// CA-46 (RF-46): los colores y las familias tipográficas viven solo en tokens.css, y los
// componentes solo usan roles. transparent, currentColor e inherit no son colores literales (D51).
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const FRONTEND = path.resolve(import.meta.dirname, '../../..');
const SRC = path.join(FRONTEND, 'src');
const TOKENS = fs.readFileSync(path.join(SRC, 'shared/marca/tokens.css'), 'utf8');

// Los 148 colores con nombre de CSS Color 4.
const NOMBRES = `aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue
blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan
darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen
darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey
darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite
forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink
indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral
lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen
lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta
maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue
mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen
paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red
rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue
slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white
whitesmoke yellow yellowgreen`.split(/\s+/);
const NOMBRE = new RegExp(`^(?:${NOMBRES.join('|')})$`, 'i');
const FUNCIONES = /(?:#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklch)\(|\b0x[0-9a-f]{6}\b)/i;
const PRIMITIVO = /--q-(?:(?:pizarra|naranja|cian|marron|ambar|crema|gris)-\d+|blanco)\b/;

/** Lo que cada fichero `.ts` o `.css` de `directorio` hace mal, sin contar tests ni tokens.css. */
function infracciones(directorio: string): string[] {
  const ficheros = fs
    .readdirSync(directorio, { recursive: true, encoding: 'utf8' })
    .filter((f) => /\.(ts|css)$/.test(f) && !f.endsWith('.test.ts'))
    .filter((f) => path.basename(f) !== 'tokens.css');
  return ficheros.flatMap((f) => {
    const texto = fs.readFileSync(path.join(directorio, f), 'utf8');
    const valores = f.endsWith('.css')
      ? [...texto.matchAll(/:\s*([^;{}]+)[;}]/g)].flatMap((m) => (m[1] ?? '').split(/[\s,()]+/))
      : [...texto.matchAll(/(['"`])([^'"`\n]*)\1/g)].map((m) => m[2] ?? '');
    const motivos = [
      FUNCIONES.test(texto) && 'color literal',
      valores.some((v) => NOMBRE.test(v.trim())) && 'color con nombre',
      /font-family|fontFamily/.test(texto) && 'font-family',
      PRIMITIVO.test(texto) && 'primitivo en lugar de rol',
    ].filter(Boolean);
    return motivos.map((motivo) => `${f.replaceAll('\\', '/')}: ${motivo}`);
  });
}

describe('literales fuera de tokens.css (CA-46)', () => {
  it('los fixtures prohibidos se detectan y los permitidos no (control positivo)', () => {
    expect(infracciones(path.join(FRONTEND, 'test/fixtures/tokens')).sort()).toEqual([
      'fill.ts: color con nombre',
      'hex.ts: color literal',
      'nombres.css: color con nombre',
      'primitivo.css: primitivo en lugar de rol',
    ]);
  });

  it('src/ no tiene ninguno', () => {
    expect(infracciones(SRC)).toEqual([]);
  });

  it('toda var(--q-…) que se usa está definida en tokens.css', () => {
    const definidas = new Set([...TOKENS.matchAll(/(--q-[\w-]+)\s*:/g)].map((m) => m[1]));
    const usadas = fs
      .readdirSync(SRC, { recursive: true, encoding: 'utf8' })
      .filter((f) => /\.(ts|css)$/.test(f) && !f.endsWith('.test.ts'))
      .flatMap((f) => [...fs.readFileSync(path.join(SRC, f), 'utf8').matchAll(/var\((--q-[\w-]+)/g)])
      .map((m) => m[1]);
    expect(usadas.length).toBeGreaterThan(0);
    expect([...new Set(usadas)].filter((u) => !definidas.has(u))).toEqual([]);
  });
});
