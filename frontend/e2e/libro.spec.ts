// Verificador determinista de la validación visual (docs/validacion-visual.md): lo mismo que la
// skill validar-visual hace con el navegador MCP, sin modelo. Portada y dedicatoria, índice (un
// enlace por capítulo cerrado y cada uno abre su capítulo) y ficha (cada entrada con al menos un
// enlace, que navega). Cada comprobación que falla nombra el rol al que se devuelve.
//
//   VISUAL_SLUG=regalo-24                      novela a revisar (por defecto, la de preparar.ts)
//   VISUAL_INFORME=<ruta>.json                 escribe el informe para `novela registrar-visual`
//   VISUAL_CAPTURAS=<directorio>               guarda las capturas de portada, capítulo y libro
import fs from 'node:fs';
import path from 'node:path';
import type { Page } from '@playwright/test';
import { API, expect, test } from './comun';

const SLUG = process.env.VISUAL_SLUG ?? 'regalo-24';
type Id = 'portada' | 'dedicatoria' | 'indice' | 'navegacion' | 'ficha';
type Rol = 'escritor' | 'exportacion' | 'frontend';
interface Comprobacion {
  id: Id;
  ok: boolean;
  detalle: string;
  responsable?: Rol;
}
interface Libro {
  titulo: string;
  dedicatoria: string | null;
  capitulos: { capitulo: number; titulo: string }[];
  personajes: { id: string; nombre: string; capitulos: number[] }[];
  lugares: { id: string; nombre: string; capitulos: number[] }[];
}

const ok = (id: Id, detalle = ''): Comprobacion => ({ id, ok: true, detalle });
const fallo = (id: Id, responsable: Rol, detalle: string): Comprobacion => ({ id, ok: false, detalle, responsable });
const por = (page: Page, testid: string) => page.locator(`[data-testid="${testid}"]`);

/** Abre el capítulo desde un enlace del libro y devuelve el título del lector, o null si no abre. */
async function abrir(page: Page, enlace: ReturnType<Page['locator']>): Promise<{ titulo: string; texto: string } | null> {
  await enlace.click();
  const lector = por(page, 'lector');
  try {
    await expect(lector.locator('.q-lector__texto')).toBeVisible({ timeout: 5_000 });
  } catch {
    return null;
  }
  const resultado = { titulo: (await por(page, 'lector-titulo').textContent()) ?? '', texto: (await lector.locator('.q-lector__texto').textContent()) ?? '' };
  await page.keyboard.press('Escape');
  await expect(lector).toHaveCount(0);
  return resultado;
}

test(`validación visual de la lectura de ${SLUG}`, async ({ page, request }) => {
  test.setTimeout(120_000);
  const libro = (await (await request.get(`${API}/novelas/${SLUG}/libro`)).json()) as Libro;
  const punto = (await (await request.get(`${API}/novelas/${SLUG}/checkpoint`)).json()) as { capitulo: number } | null;
  const cerrados = punto?.capitulo ?? 0;
  const capturas = process.env.VISUAL_CAPTURAS;
  const foto = async (nombre: string, locator?: ReturnType<Page['locator']>) => {
    if (!capturas) return;
    fs.mkdirSync(capturas, { recursive: true });
    const ruta = path.join(capturas, `lectura-${nombre}.png`);
    await (locator ?? page).screenshot({ path: ruta });
    rutas.push(ruta);
  };
  const rutas: string[] = [];
  const resultado: Comprobacion[] = [];

  await page.goto(`/#/novelas/${SLUG}/lectura`);
  await expect(por(page, 'libro')).toBeVisible();

  // Portada y dedicatoria
  const titulo = (await por(page, 'portada-titulo').textContent()) ?? '';
  resultado.push(titulo.trim() && titulo === libro.titulo ? ok('portada', titulo) : fallo('portada', 'frontend', `título «${titulo}», se esperaba «${libro.titulo}»`));
  const dedicatoria = por(page, 'portada-dedicatoria');
  if (!libro.dedicatoria) resultado.push(fallo('dedicatoria', 'exportacion', 'el libro no trae dedicatoria: ¿falta brief/brief.json?'));
  else if ((await dedicatoria.count()) === 0 || (await dedicatoria.textContent()) !== libro.dedicatoria)
    resultado.push(fallo('dedicatoria', 'frontend', 'la dedicatoria del libro no se pinta en la portada'));
  else resultado.push(ok('dedicatoria'));
  await foto('portada', por(page, 'portada'));

  // Índice: un enlace por capítulo cerrado, con título, y cada uno navega
  const enlaces = por(page, 'indice-capitulo');
  const n = await enlaces.count();
  if (libro.capitulos.length !== cerrados) resultado.push(fallo('indice', 'exportacion', `el libro trae ${libro.capitulos.length} capítulos y hay ${cerrados} cerrados`));
  else if (n !== cerrados) resultado.push(fallo('indice', 'frontend', `${n} enlaces para ${cerrados} capítulos cerrados`));
  else if (libro.capitulos.some((c) => !c.titulo.trim())) resultado.push(fallo('indice', 'escritor', 'un capítulo sin título'));
  else resultado.push(ok('indice', `${n} enlaces`));

  const rotos: string[] = [];
  const vacios: number[] = [];
  for (let i = 0; i < n; i++) {
    const esperado = libro.capitulos[i];
    const visto = await abrir(page, enlaces.nth(i));
    if (!visto || visto.titulo !== esperado?.titulo) rotos.push(`${i + 1}`);
    else if (!visto.texto.trim()) vacios.push(i + 1);
    if (i === 0 && visto) {
      await enlaces.nth(0).click();
      await expect(por(page, 'lector').locator('.q-lector__texto')).toBeVisible();
      await foto('capitulo', por(page, 'lector'));
      await page.keyboard.press('Escape');
    }
  }
  if (rotos.length) resultado.push(fallo('navegacion', 'frontend', `no abren su capítulo: ${rotos.join(', ')}`));
  else if (vacios.length) resultado.push(fallo('navegacion', 'escritor', `capítulos sin texto: ${vacios.join(', ')}`));
  else resultado.push(ok('navegacion', `${n} capítulos abiertos desde el índice`));

  // Ficha: cada personaje y lugar con al menos un enlace, y el primero de cada uno navega
  const entradas = por(page, 'ficha-entrada');
  const total = libro.personajes.length + libro.lugares.length;
  const sinEnlace: string[] = [];
  const fichaRota: string[] = [];
  for (let i = 0; i < (await entradas.count()); i++) {
    const entrada = entradas.nth(i);
    const id = (await entrada.getAttribute('data-entidad')) ?? '?';
    const suyos = entrada.locator('[data-testid="ficha-enlace"]');
    if ((await suyos.count()) === 0) {
      sinEnlace.push(id);
      continue;
    }
    const destino = Number(await suyos.first().getAttribute('data-destino'));
    const visto = await abrir(page, suyos.first());
    if (visto?.titulo !== libro.capitulos.find((c) => c.capitulo === destino)?.titulo) fichaRota.push(id);
  }
  await foto('libro', por(page, 'libro'));
  if (libro.personajes.length === 0) resultado.push(fallo('ficha', 'escritor', 'ningún personaje aparece en los capítulos cerrados'));
  else if ((await entradas.count()) !== total) resultado.push(fallo('ficha', 'frontend', `${await entradas.count()} entradas pintadas de ${total}`));
  else if (sinEnlace.length) resultado.push(fallo('ficha', 'exportacion', `sin enlace a capítulo: ${sinEnlace.join(', ')}`));
  else if (fichaRota.length) resultado.push(fallo('ficha', 'frontend', `el enlace no abre su capítulo: ${fichaRota.join(', ')}`));
  else resultado.push(ok('ficha', `${libro.personajes.length} personajes y ${libro.lugares.length} lugares`));

  const informe = process.env.VISUAL_INFORME;
  if (informe) {
    const capturasRel = rutas.map((r) => path.relative(path.join(import.meta.dirname, '..', '..'), r).replaceAll('\\', '/'));
    const cuerpo = { schema_version: '1.0.0', slug: SLUG, herramienta: 'playwright-test', comprobaciones: resultado, capturas: capturasRel };
    fs.writeFileSync(informe, JSON.stringify(cuerpo, null, 2) + '\n');
  }
  expect(resultado.filter((c) => !c.ok)).toEqual([]);
});
