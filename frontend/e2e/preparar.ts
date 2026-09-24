// Antes de los e2e: los tres workspaces de panel.py (§13); hostil-24, una copia de demo-24 cuyo
// capítulo 3, ya cerrado, lleva el cuerpo hostil de CA-26 con su frontmatter intacto; y regalo-24,
// demo-24 con el brief ficticio de backend/tests/fixtures, para la dedicatoria de e2e/libro.spec.ts.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { NOVELAS } from '../playwright.config';

const BACKEND = path.join(import.meta.dirname, '..', '..', 'backend');
const HOSTIL = path.join(import.meta.dirname, '..', 'test', 'fixtures', 'capitulos', 'hostil.md');
const BRIEF = path.join(BACKEND, 'tests', 'fixtures', 'brief', 'brief-completo.json');

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
  // regalo-24: demo-24 con el brief ficticio, para la dedicatoria de e2e/libro.spec.ts.
  const regalo = path.join(NOVELAS, 'regalo-24');
  fs.cpSync(path.join(NOVELAS, 'demo-24'), regalo, { recursive: true });
  fs.mkdirSync(path.join(regalo, 'brief'), { recursive: true });
  fs.copyFileSync(BRIEF, path.join(regalo, 'brief', 'brief.json'));
}
