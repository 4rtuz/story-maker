// CA-57 y RNF-24, parte unitaria y estática. jsdom no calcula :hover ni :focus-visible (VER-13):
// aquí se comprueba que estilos.css los declara para cada componente interactivo, con el foco
// en outline y la transición en --q-transicion; lo que se ve lo mide marca.spec.ts.
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { boton } from './componentes';

const CSS = ['estilos.css', '../../app/app.css']
  .map((f) => fs.readFileSync(path.join(import.meta.dirname, f), 'utf8'))
  .join('\n');
const TOKENS = fs.readFileSync(path.join(import.meta.dirname, '../marca/tokens.css'), 'utf8');

/** Las declaraciones de cada selector, sin comentarios y fuera de @media. */
function reglas(css: string): Map<string, string> {
  const sin = css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/@media[^{]*\{([^{}]*\{[^}]*\})*\s*\}/g, '');
  const mapa = new Map<string, string>();
  for (const [, selectores = '', cuerpo = ''] of sin.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
    for (const s of selectores.split(',')) {
      const clave = s.trim().replace(/\s+/g, ' ');
      mapa.set(clave, (mapa.get(clave) ?? '') + cuerpo);
    }
  }
  return mapa;
}

interface Interactivo {
  nombre: string;
  reposo: string;
  hover: string;
  foco: string;
  deshabilitado?: string;
}

// Cada tarea que añade un componente interactivo lo añade aquí (spec 0004 §8.4).
const INTERACTIVOS: Interactivo[] = [
  {
    nombre: 'botón primario',
    reposo: '.q-boton',
    hover: '.q-boton--primario:hover',
    foco: '.q-boton:focus-visible',
    deshabilitado: '.q-boton:disabled',
  },
  {
    nombre: 'botón secundario',
    reposo: '.q-boton',
    hover: '.q-boton--secundario:hover',
    foco: '.q-boton:focus-visible',
    deshabilitado: '.q-boton:disabled',
  },
  {
    nombre: 'ítem de navegación',
    reposo: '.q-nav__item',
    hover: '.q-nav__item:hover',
    foco: '.q-nav__item:focus-visible',
  },
  {
    nombre: 'botón de plegar',
    reposo: '.q-plegar',
    hover: '.q-plegar:hover',
    foco: '.q-plegar:focus-visible',
  },
  {
    nombre: 'enlace de una novela de la biblioteca',
    reposo: '.q-obra__enlace',
    hover: '.q-obra__enlace:hover',
    foco: '.q-obra__enlace:focus-visible',
  },
  {
    nombre: 'tarjeta de novela nueva',
    reposo: '.q-obra--nueva',
    hover: '.q-obra--nueva:hover',
    foco: '.q-obra--nueva:focus-visible',
  },
  {
    nombre: 'desplegable de datos de la gráfica',
    reposo: '.q-detalles__resumen',
    hover: '.q-detalles__resumen:hover',
    foco: '.q-detalles__resumen:focus-visible',
  },
  {
    nombre: 'opción del chat',
    reposo: '.q-chip-opcion',
    hover: '.q-chip-opcion:hover',
    foco: '.q-chip-opcion:focus-visible',
  },
  {
    nombre: 'entrada del chat',
    reposo: '.q-chat__texto',
    hover: '.q-chat__texto:hover',
    foco: '.q-chat__texto:focus-visible',
  },
  {
    nombre: 'botón de enviar del chat',
    reposo: '.q-chat__enviar',
    hover: '.q-chat__enviar:hover',
    foco: '.q-chat__enviar:focus-visible',
  },
  {
    nombre: 'enlace de un lanzamiento',
    reposo: '.q-tarea__ver',
    hover: '.q-tarea__ver:hover',
    foco: '.q-tarea__ver:focus-visible',
  },
  {
    nombre: 'selector de medida de las métricas',
    reposo: '.q-selector__opcion',
    hover: '.q-selector__opcion:hover',
    foco: '.q-selector__opcion:focus-visible',
  },
];

describe.each(INTERACTIVOS)('$nombre', ({ reposo, hover, foco, deshabilitado }) => {
  const css = reglas(CSS);

  it('declara hover y, donde aplica, deshabilitado, distintos del reposo', () => {
    expect(css.get(hover)?.trim()).toBeTruthy();
    if (deshabilitado) expect(css.get(deshabilitado)?.trim()).toBeTruthy();
  });

  it('marca el foco con outline de --q-contorno-foco en --q-foco o --q-foco-sobre-oscuro', () => {
    const cuerpo = css.get(foco) ?? '';
    expect(cuerpo).toMatch(/outline:\s*var\(--q-contorno-foco\)\s+solid\s+var\(--q-foco(-sobre-oscuro)?\)/);
    expect(cuerpo).not.toMatch(/box-shadow/);
  });

  it('transiciona con --q-transicion', () => {
    expect(css.get(reposo) ?? '').toMatch(/transition:[^;]*var\(--q-transicion\)/);
  });
});

describe('movimiento reducido', () => {
  it('--q-transicion pasa a 0 con prefers-reduced-motion: reduce', () => {
    expect(TOKENS).toMatch(
      /@media \(prefers-reduced-motion: reduce\)\s*\{\s*:root\s*\{\s*--q-transicion:\s*0ms;/,
    );
  });

  it('los esqueletos no se animan con movimiento reducido', () => {
    expect(CSS).toMatch(/@media \(prefers-reduced-motion: reduce\)\s*\{[^}]*\.q-esqueleto[^}]*animation:\s*none/);
  });
});

describe('construcción', () => {
  it('el botón es type=button y se deshabilita con el atributo', () => {
    const b = boton('Copiar', { variante: 'secundario', deshabilitado: true });
    expect(b.type).toBe('button');
    expect(b.disabled).toBe(true);
    expect(b.className).toContain('q-boton--secundario');
  });

  it('el secundario lleva la flecha a la derecha, oculta a los lectores', () => {
    const b = boton('Ver progreso', { variante: 'secundario', flecha: true });
    expect(b.textContent).toBe('Ver progreso→');
    expect(b.lastElementChild?.getAttribute('aria-hidden')).toBe('true');
  });
});
