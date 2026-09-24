// CA-25 y CA-26 en su parte unitaria, VAL-16 y VAL-17: el lector quita el frontmatter, renderiza el
// markdown sin HTML, enlaces ni imágenes, y el título del índice entra como texto.
import fs from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { arrancar } from '../../app/rutas';
import { cuerpoDeCapitulo, quitarFrontmatter } from './lector';
import { lectura } from './vista';
import { INDICE, json, servirLectura } from './servir-lectura.test-util';

const FIXTURES = path.join(import.meta.dirname, '../../../test/fixtures/capitulos');
const leer = (nombre: string) => fs.readFileSync(path.join(FIXTURES, nombre), 'utf8');

const ACTIVOS = 'script, iframe, img, a, object, embed, svg';
const conAtributoOn = (raiz: Element) =>
  [raiz, ...raiz.querySelectorAll('*')].filter((e) => [...e.attributes].some((a) => a.name.toLowerCase().startsWith('on')));

describe('frontmatter (D16)', () => {
  it('quita el bloque inicial y nada más', () => {
    const texto = quitarFrontmatter(leer('frontmatter.md'));
    expect(texto).not.toContain('run_id:');
    expect(texto.trimStart().startsWith('# Capítulo 3')).toBe(true);
    expect(texto).toContain('---'); // la regla horizontal del cuerpo sigue
  });

  it('sin frontmatter, el texto queda igual', () => {
    expect(quitarFrontmatter('Hola\n\n---\n\nAdiós\n')).toBe('Hola\n\n---\n\nAdiós\n');
  });

  it('con CRLF pierde el frontmatter y conserva su <hr> del cuerpo (VAL-16)', () => {
    const crudo = leer('frontmatter-crlf.md');
    expect(crudo).toContain('\r\n'); // control: git no ha convertido el fixture
    const cuerpo = cuerpoDeCapitulo(crudo);
    expect(cuerpo.textContent).not.toContain('run_id:');
    expect(cuerpo.textContent).toContain('Primera parte');
    expect(cuerpo.textContent).toContain('Segunda parte');
    expect(cuerpo.querySelectorAll('hr')).toHaveLength(1);
  });
});

describe('markdown hostil (CA-26, RNF-07)', () => {
  const FRAGMENTOS = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '<iframe src="http://ejemplo.invalid">',
    '[pulsa](javascript:alert(1))',
    '![x](http://ejemplo.invalid/x.png)',
    '<http://ejemplo.invalid>',
    '[a][r]',
    '[r]: javascript:alert(1)',
    '![x][i]',
    '[i]: http://ejemplo.invalid/x.png',
    'Suelto: http://ejemplo.invalid',
    '<svg onload=alert(1)>',
    '[x](data:text/html,hola)',
  ];

  it('ningún elemento activo ni atributo on*, y cada fragmento como texto', () => {
    const cuerpo = cuerpoDeCapitulo(leer('hostil.md'));
    expect(cuerpo.querySelectorAll(ACTIVOS)).toHaveLength(0);
    expect(conAtributoOn(cuerpo)).toEqual([]);
    for (const fragmento of FRAGMENTOS) expect(cuerpo.textContent).toContain(fragmento);
  });

  it('el markdown corriente sí se renderiza (control positivo)', () => {
    const cuerpo = cuerpoDeCapitulo(leer('frontmatter.md'));
    expect(cuerpo.querySelector('h1')?.textContent).toBe('Capítulo 3');
    expect(cuerpo.querySelector('em')?.textContent).toBe('forzada');
  });
});

describe('el lector en la vista (CA-25)', () => {
  let parar: (() => void) | undefined;
  let raiz: HTMLElement;

  beforeEach(() => {
    vi.useFakeTimers();
    raiz = document.createElement('div');
    document.body.replaceChildren(raiz);
  });

  afterEach(() => {
    parar?.();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  function abrirTres(indice: unknown[]): void {
    servirLectura({ '/capitulos': json(indice), '/capitulos/3': () => new Response(leer('frontmatter.md')) });
    location.hash = '#/novelas/demo-24/lectura/3';
    parar = arrancar(raiz, (ruta, navegar) => lectura(ruta as { vista: 'lectura'; slug: string }, navegar)).detener;
  }

  it('el 3 con el título del índice y sin frontmatter', async () => {
    abrirTres(INDICE);
    await vi.advanceTimersByTimeAsync(50);
    const dialogo = raiz.querySelector('[role="dialog"]');
    expect(dialogo?.querySelector('h2')?.textContent).toBe('Capítulo tres');
    expect(dialogo?.querySelector('.q-lector__texto h1')?.textContent).toBe('Capítulo 3');
    expect(dialogo?.textContent).not.toContain('run_id:');
    expect(dialogo?.textContent).not.toContain('schema_version');
  });

  it('un título hostil del índice queda como texto literal', async () => {
    const hostil = '<img src=x onerror=alert(1)>';
    abrirTres(INDICE.map((c) => (c.capitulo === 3 ? { ...c, titulo: hostil } : c)));
    await vi.advanceTimersByTimeAsync(50);
    const dialogo = raiz.querySelector('[role="dialog"]');
    expect(dialogo?.querySelector('h2')?.textContent).toBe(hostil);
    // El único img de la página es el logo del layout: ni el diálogo ni la lista tienen ninguno.
    expect(raiz.querySelectorAll('[role="dialog"] img, .q-volumenes img')).toHaveLength(0);
    expect(raiz.querySelector('[data-capitulo="3"]')?.textContent).toContain(hostil);
  });
});
