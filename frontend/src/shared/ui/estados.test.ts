// CA-57 y RNF-24, parte unitaria y estática. jsdom no calcula :hover ni :focus-visible (VER-13):
// aquí se comprueba que estilos.css los declara para cada componente interactivo, con el foco
// en outline y la transición en --q-transicion; lo que se ve lo mide marca.spec.ts.
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { boton, campo } from './componentes';

const CSS = fs.readFileSync(path.join(import.meta.dirname, 'estilos.css'), 'utf8');
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
    nombre: 'campo de formulario',
    reposo: '.q-campo__control',
    hover: '.q-campo__control:hover',
    foco: '.q-campo__control:focus-visible',
    deshabilitado: '.q-campo__control:disabled',
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

  it('el campo lleva la etiqueta encima y el error debajo, enlazado', () => {
    const c = campo({ id: 'slug', etiqueta: 'Slug' });
    c.mostrarError('no casa ^[a-z0-9-]+$');
    const [etiqueta, control, error] = [...c.raiz.children];
    expect(etiqueta?.tagName).toBe('LABEL');
    expect(control).toBe(c.control);
    expect(c.control.getAttribute('aria-invalid')).toBe('true');
    expect(c.control.getAttribute('aria-describedby')).toBe(error?.id);
    expect(error?.textContent).toBe('no casa ^[a-z0-9-]+$');
    c.mostrarError(null);
    expect(c.control.hasAttribute('aria-invalid')).toBe(false);
  });

  it('nada se inserta como HTML', () => {
    const c = campo({ id: 'x', etiqueta: '<img src=x onerror=alert(1)>' });
    expect(c.raiz.querySelector('img')).toBeNull();
  });
});
