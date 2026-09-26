// La portada, el índice y la ficha de la lectura web (docs/lectura-web.md), con los data-testid que
// usan la skill validar-visual y e2e/libro.spec.ts.
import { describe, expect, it } from 'vitest';
import { libro } from './libro';

const LIBRO = {
  titulo: 'demo-regalo',
  dedicatoria: 'Para Aurora Ficticia, en el día de su boda.',
  capitulos: [
    { capitulo: 1, titulo: 'La linterna' },
    { capitulo: 2, titulo: 'El archivo' },
  ],
  personajes: [{ id: 'per-elena-vidal', nombre: 'Elena Vidal', detalle: 'la farera', capitulos: [1, 2] }],
  lugares: [{ id: 'esc-archivo', nombre: 'El archivo', detalle: null, capitulos: [2] }],
};

const q = (raiz: HTMLElement, testid: string) => [...raiz.querySelectorAll<HTMLElement>(`[data-testid="${testid}"]`)];

describe('libro', () => {
  it('portada con título y dedicatoria', () => {
    const raiz = libro(LIBRO, 'demo-regalo');
    expect(q(raiz, 'portada-titulo')[0]?.textContent).toBe('demo-regalo');
    expect(q(raiz, 'portada-dedicatoria')[0]?.textContent).toBe('Para Aurora Ficticia, en el día de su boda.');
  });

  it('la portada invita a empezar por el capítulo 1', () => {
    const empezar = q(libro(LIBRO, 'demo-regalo'), 'portada-empezar')[0];
    expect(empezar?.getAttribute('href')).toBe('#/novelas/demo-regalo/lectura/1');
    expect(q(libro({ ...LIBRO, capitulos: [] }, 'demo-regalo'), 'portada-empezar')).toEqual([]);
  });

  it('sin dedicatoria, no la pinta', () => {
    expect(q(libro({ ...LIBRO, dedicatoria: null }, 'demo-regalo'), 'portada-dedicatoria')).toEqual([]);
  });

  it('un enlace del índice por capítulo, a su ruta de lectura', () => {
    const enlaces = q(libro(LIBRO, 'demo-regalo'), 'indice-capitulo') as HTMLAnchorElement[];
    expect(enlaces.map((a) => a.getAttribute('href'))).toEqual([
      '#/novelas/demo-regalo/lectura/1',
      '#/novelas/demo-regalo/lectura/2',
    ]);
    expect(enlaces[1]?.textContent).toBe('2. El archivo');
  });

  it('cada entrada de la ficha enlaza a los capítulos en que aparece', () => {
    const entradas = q(libro(LIBRO, 'demo-regalo'), 'ficha-entrada');
    expect(entradas.map((e) => [e.dataset.entidad, e.dataset.tipo])).toEqual([
      ['per-elena-vidal', 'personaje'],
      ['esc-archivo', 'lugar'],
    ]);
    const enlaces = q(entradas[0]!, 'ficha-enlace');
    expect(enlaces.map((a) => a.getAttribute('href'))).toEqual([
      '#/novelas/demo-regalo/lectura/1',
      '#/novelas/demo-regalo/lectura/2',
    ]);
    // Compactos: el número a la vista y el título como nombre accesible (docs/validacion-visual.md).
    expect(enlaces.map((a) => a.textContent)).toEqual(['1', '2']);
    expect(enlaces[0]?.getAttribute('aria-label')).toBe('Capítulo 1 — La linterna');
  });

  it('el texto del workspace entra como texto, nunca como HTML', () => {
    const raiz = libro({ ...LIBRO, titulo: '<img src=x onerror=alert(1)>' }, 'demo-regalo');
    expect(raiz.querySelector('img')).toBeNull();
  });
});
