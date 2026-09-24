// Reglas del panel (spec 0004, §8.2). Cada una entra en la tarea que la prueba (PD2) y ninguna
// lleva excepción por fichero: lo que se permite, se permite con un eslint-disable-next-line
// visible en el código (D56). Los fixtures de test/fixtures/lint/ los lintea lint.test.ts.
import path from 'node:path';
import js from '@eslint/js';
import noUnsanitized from 'eslint-plugin-no-unsanitized';
import tseslint from 'typescript-eslint';

const SRC = path.join(import.meta.dirname, 'src');

/** RF-43: nada de fuera de src/, en particular de novelas/ ni de backend/. */
const soloDeSrc = {
  meta: {
    type: 'problem',
    messages: { fuera: 'import de fuera de src/: {{ruta}} (RF-43)' },
    schema: [],
  },
  create(context) {
    const comprobar = (nodo) => {
      const ruta = nodo.source?.value;
      if (typeof ruta !== 'string' || !/^[./]/.test(ruta)) return;
      const destino = path.resolve(path.dirname(context.filename), ruta.split('?')[0]);
      const relativa = path.relative(SRC, destino);
      if (relativa.startsWith('..') || path.isAbsolute(relativa)) {
        context.report({ node: nodo.source, messageId: 'fuera', data: { ruta } });
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

export default tseslint.config(
  { ignores: ['dist/', 'node_modules/', 'test/fixtures/', 'playwright-report/', 'test-results/'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  noUnsanitized.configs.recommended,
  {
    files: ['src/**/*.ts'],
    plugins: { panel: { rules: { 'solo-de-src': soloDeSrc } } },
    rules: { 'panel/solo-de-src': 'error' },
  },
);
