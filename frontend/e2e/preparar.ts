// Antes de los e2e: los tres workspaces de panel.py (§13) y hostil-24, una copia de demo-24 cuyo
// capítulo 3, ya cerrado, lleva el cuerpo hostil de CA-26 con su frontmatter intacto.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { NOVELAS } from '../playwright.config';

const BACKEND = path.join(import.meta.dirname, '..', '..', 'backend');
const HOSTIL = path.join(import.meta.dirname, '..', 'test', 'fixtures', 'capitulos', 'hostil.md');

/** El texto a partir del cierre del frontmatter, o entero si no lo tiene. */
const cuerpo = (texto: string): string => texto.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
const frontmatter = (texto: string): string => texto.slice(0, texto.length - cuerpo(texto).length);

export default function preparar(): void {
  fs.rmSync(NOVELAS, { recursive: true, force: true });
  execFileSync('uv', ['run', 'python', '-m', 'tests.fixtures.panel', NOVELAS], { cwd: BACKEND, stdio: 'inherit' });
  const hostil = path.join(NOVELAS, 'hostil-24');
  fs.cpSync(path.join(NOVELAS, 'demo-24'), hostil, { recursive: true });
  const tres = path.join(hostil, 'capitulos', '03.md');
  const original = fs.readFileSync(tres, 'utf8');
  fs.writeFileSync(tres, frontmatter(original) + cuerpo(fs.readFileSync(HOSTIL, 'utf8')));
}
