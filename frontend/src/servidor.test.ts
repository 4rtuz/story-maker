// @vitest-environment node
// El dev server de Vite contra RF-01 y RF-43: puerto fijo y ningún fichero de fuera de frontend/.
// Las peticiones van con node:http y no con fetch, que normalizaría `..` antes de salir.
import fs from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import { createServer, type ViteDevServer } from 'vite';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

const FRONTEND = path.resolve(import.meta.dirname, '..');
const RAIZ = path.resolve(FRONTEND, '..').replaceAll('\\', '/');
const CONFIG = path.join(FRONTEND, 'vite.config.ts');
const PUERTO = 5173;

// Un workspace sintético con un canario en el sitio del secreto: si alguna ruta lo sirve, el
// cuerpo lo delata. Slug propio para no pisar nunca una novela real.
const CANARIO = 'CANARIO-DEL-CANON-no-debe-servirse';
const SLUG = `canario-servidor-${process.pid}`;
const SECRETO = ['novelas', SLUG, 'canon', 'misterio.md'].join('/');

function pedir(ruta: string): Promise<{ status: number; cuerpo: string }> {
  return new Promise((resolver, rechazar) => {
    const peticion = http.get({ host: 'localhost', port: PUERTO, path: ruta }, (respuesta) => {
      let cuerpo = '';
      respuesta.setEncoding('utf8');
      respuesta.on('data', (trozo: string) => (cuerpo += trozo));
      respuesta.on('end', () => resolver({ status: respuesta.statusCode ?? 0, cuerpo }));
    });
    peticion.on('error', rechazar);
  });
}

async function arrancar(): Promise<ViteDevServer> {
  const servidor = await createServer({ configFile: CONFIG, logLevel: 'silent' });
  await servidor.listen();
  return servidor;
}

describe('puerto', () => {
  it('con el 5173 ocupado, el arranque falla en vez de cambiar de puerto', async () => {
    const ocupante = net.createServer();
    await new Promise<void>((listo) => ocupante.listen(PUERTO, 'localhost', listo));
    const servidor = await createServer({ configFile: CONFIG, logLevel: 'silent' });
    try {
      await expect(servidor.listen()).rejects.toThrow(/5173/);
    } finally {
      await servidor.close();
      await new Promise((listo) => ocupante.close(listo));
    }
  });

  it('libre, escucha en http://localhost:5173', async () => {
    const servidor = await arrancar();
    try {
      expect(servidor.resolvedUrls?.local).toContain('http://localhost:5173/');
    } finally {
      await servidor.close();
    }
  });
});

describe.each([
  ['frontend/', FRONTEND],
  ['la raíz del repositorio', RAIZ],
])('/@fs/ con el servidor arrancado desde %s', (_, directorio) => {
  let servidor: ViteDevServer | undefined;
  const antes = process.cwd();

  beforeAll(async () => {
    fs.mkdirSync(path.dirname(path.join(RAIZ, SECRETO)), { recursive: true });
    fs.writeFileSync(path.join(RAIZ, SECRETO), `# Misterio\n\n${CANARIO}\n`);
    process.chdir(directorio);
    servidor = await arrancar();
  });

  afterAll(async () => {
    fs.rmSync(path.join(RAIZ, 'novelas', SLUG), { recursive: true, force: true });
    process.chdir(antes);
    await servidor?.close();
  });

  it('sirve lo de frontend/ (control positivo) y niega AGENTS.md con 403', async () => {
    expect((await pedir(`/@fs/${RAIZ}/frontend/src/main.ts`)).status).toBe(200);
    expect((await pedir(`/@fs/${RAIZ}/AGENTS.md`)).status).toBe(403);
  });

  it.each([
    `/@fs/${RAIZ}/${SECRETO}`,
    `/@fs/${RAIZ}/backend/api/main.py`,
    `/@fs/${RAIZ}/frontend/../AGENTS.md`,
    '/%2e%2e/AGENTS.md',
    '/../AGENTS.md',
    '/src/../../AGENTS.md?raw',
  ])('%s no se sirve', async (ruta) => {
    const { status, cuerpo } = await pedir(ruta);
    expect(status).not.toBe(200);
    expect(cuerpo).not.toContain('# AGENTS.md');
    expect(cuerpo).not.toContain(CANARIO);
  });
});
