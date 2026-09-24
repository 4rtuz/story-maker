// Reglas del panel (spec 0004, §8.2). Cada una entra en la tarea que la prueba (PD2) y ninguna
// lleva excepción por fichero: lo que se permite, se permite con un eslint-disable-next-line
// visible en el código (D56). Los fixtures de test/fixtures/lint/ los lintea lint.test.ts.
import path from 'node:path';
import js from '@eslint/js';
import noUnsanitized from 'eslint-plugin-no-unsanitized';
import tseslint from 'typescript-eslint';

const SRC = path.join(import.meta.dirname, 'src');
const MARCA = path.join(SRC, 'shared', 'marca');

/** Una regla que mira a dónde resuelve cada import relativo del fichero. */
function porDestino(mensaje, prohibido) {
  return {
    meta: { type: 'problem', messages: { prohibido: mensaje }, schema: [] },
    create(context) {
      const comprobar = (nodo) => {
        const ruta = nodo.source?.value;
        if (typeof ruta !== 'string' || !/^[./]/.test(ruta)) return;
        const destino = path.resolve(path.dirname(context.filename), ruta.split('?')[0]);
        if (prohibido(destino, path.resolve(context.filename))) {
          context.report({ node: nodo.source, messageId: 'prohibido', data: { ruta } });
        }
      };
      return {
        ImportDeclaration: comprobar,
        ImportExpression: comprobar,
        ExportAllDeclaration: comprobar,
        ExportNamedDeclaration: comprobar,
      };
    },
  };
}

// RF-03: toda petición sale del cliente. Se mira el nombre y no solo la global suelta, así que
// window.fetch, globalThis['fetch'] y navigator.sendBeacon también cuentan (VER-12).
const RED = new Set(['fetch', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'sendBeacon']);
const redSoloEnApi = {
  meta: {
    type: 'problem',
    messages: { red: '{{nombre}} fuera de src/shared/api/: toda petición va por el cliente (RF-03)' },
    schema: [],
  },
  create(context) {
    const dentro = !path.relative(path.join(SRC, 'shared', 'api'), path.resolve(context.filename)).startsWith('..');
    if (dentro) return {};
    const avisar = (nodo, nombre) => context.report({ node: nodo, messageId: 'red', data: { nombre } });
    return {
      Identifier(nodo) {
        const clave = nodo.parent?.type === 'Property' && nodo.parent.key === nodo && !nodo.parent.computed;
        const tipo = nodo.parent?.type === 'TSTypeQuery'; // `typeof fetch` no pide nada
        if (RED.has(nodo.name) && !clave && !tipo) avisar(nodo, nodo.name);
      },
      Literal(nodo) {
        const indice = nodo.parent?.type === 'MemberExpression' && nodo.parent.property === nodo;
        if (indice && RED.has(nodo.value)) avisar(nodo, nodo.value);
      },
    };
  },
};

const reglas = {
  'red-solo-en-api': redSoloEnApi,
  // RF-43: nada de fuera de src/, en particular de novelas/ ni de backend/.
  'solo-de-src': porDestino('import de fuera de src/: {{ruta}} (RF-43)', (destino) => {
    const relativa = path.relative(SRC, destino);
    return relativa.startsWith('..') || path.isAbsolute(relativa);
  }),
  // RF-51: solo logo.ts muestra el logo, y siempre en su contenedor redondeado.
  'logo-solo-en-logo-ts': porDestino(
    '{{ruta}}: el logo se muestra con crearLogo() de shared/marca/logo.ts (RF-51)',
    (destino, fichero) =>
      destino === path.join(MARCA, 'logo.png') && fichero !== path.join(MARCA, 'logo.ts'),
  ),
};

export default tseslint.config(
  {
    ignores: [
      'dist/',
      'node_modules/',
      'test/fixtures/',
      'playwright-report/',
      'test-results/',
      'src/shared/api/esquema.gen.ts', // generado por `npm run tipos` (RF-02)
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  noUnsanitized.configs.recommended,
  {
    files: ['src/**/*.ts'],
    plugins: { panel: { rules: reglas } },
    rules: {
      'panel/solo-de-src': 'error',
      'panel/logo-solo-en-logo-ts': 'error',
      'panel/red-solo-en-api': 'error',
    },
  },
);
