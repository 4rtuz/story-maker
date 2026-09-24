// CA-56 (RF-56), parte unitaria: la fuente y los iconos se sirven desde frontend/, con su
// licencia al lado, y los iconos se dibujan con createElementNS desde trazados.ts.
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { icono, NOMBRES_DE_ICONO } from '../iconos/trazados';

const MARCA = import.meta.dirname;
const ICONOS = path.join(MARCA, '..', 'iconos');
const FRONTEND = path.resolve(MARCA, '../../..');

describe('fuente display', () => {
  it('es WOFF2 con OFL.txt al lado', () => {
    const fuentes = fs.readdirSync(path.join(MARCA, 'fuentes'));
    expect(fuentes.filter((f) => f !== 'OFL.txt').every((f) => f.endsWith('.woff2'))).toBe(true);
    expect(fuentes).toContain('OFL.txt');
  });

  it('se declara en tokens.css con font-display: swap', () => {
    const tokens = fs.readFileSync(path.join(MARCA, 'tokens.css'), 'utf8');
    const regla = tokens.match(/@font-face\s*{[^}]*}/)?.[0] ?? '';
    expect(regla).toMatch(/font-display:\s*swap/);
    expect(regla).toMatch(/url\(['"]?\.\/fuentes\/outfit-800\.woff2['"]?\)/);
  });
});

describe('iconos', () => {
  const trazados = fs.readFileSync(path.join(ICONOS, 'trazados.ts'), 'utf8');

  it('trazados.ts nombra su origen y su versión, y la licencia ISC está al lado', () => {
    expect(trazados).toMatch(/lucide-static[^\n]*1\.48\.0/);
    expect(trazados).toMatch(/@fontsource\/outfit[^\n]*5\.3\.0/);
    expect(fs.readFileSync(path.join(ICONOS, 'LICENSE'), 'utf8')).toMatch(/^ISC License/);
  });

  it('están los doce de la spec §8.4', () => {
    expect([...NOMBRES_DE_ICONO].sort()).toEqual(
      [
        'activity',
        'book-open',
        'chart-line',
        'circle-alert',
        'copy',
        'history',
        'library',
        'list-tree',
        'panel-left',
        'plug',
        'rocket',
        'terminal',
      ].sort(),
    );
  });

  it('se dibujan como svg con createElementNS, ocultos a los lectores y en currentColor', () => {
    const svg = icono('rocket');
    expect(svg.namespaceURI).toBe('http://www.w3.org/2000/svg');
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.getAttribute('stroke')).toBe('currentColor');
    expect(svg.querySelectorAll('path')).toHaveLength(4);
    expect([...svg.children].every((hijo) => hijo.namespaceURI === svg.namespaceURI)).toBe(true);
  });

  it('package.json sigue sin dependencias de iconos ni de fuentes (RF-44)', () => {
    const paquete = JSON.parse(fs.readFileSync(path.join(FRONTEND, 'package.json'), 'utf8')) as {
      dependencies: Record<string, string>;
    };
    expect(Object.keys(paquete.dependencies).sort()).toEqual(['markdown-it', 'three']);
  });
});
