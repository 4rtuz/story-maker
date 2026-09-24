// Lectura en el navegador: estados de la estantería, lector, capítulo hostil, sin WebGL, cámara con
// reduced motion, draw calls y entradas y salidas repetidas (CA-24 a CA-26, CA-29, CA-30, RNF-03;
// VAL-7, VAL-18, VAL-19, VAL-20).
import { chromium } from '@playwright/test';
import { aLaApi, API, expect, test } from './comun';

const escena = (page: import('@playwright/test').Page) => page.locator('.q-escena');

/** Dos fotogramas: data-draw-calls es el del último dibujado, nunca el de antes del primero (VER-23). */
const dosFotogramas = (page: import('@playwright/test').Page) =>
  page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));

test('24 volúmenes: 7 cerrados, el 8 en curso y del 9 al 24 pendientes (CA-24)', async ({ page }) => {
  await page.goto('/#/novelas/demo-24/lectura');
  await expect(escena(page)).toHaveAttribute('data-volumenes', '24');
  const estados = await page.locator('.q-volumenes [data-capitulo]').evaluateAll((bs) => bs.map((b) => b.getAttribute('data-estado')));
  expect(estados).toEqual([...Array(7).fill('cerrado'), 'en_curso', ...Array(16).fill('pendiente')]);
});

test('abrir el 3 pide su texto y muestra el título del índice sin frontmatter (CA-25)', async ({ page, red, request }) => {
  const indice = (await (await request.get(`${API}/novelas/demo-24/capitulos`)).json()) as { capitulo: number; titulo: string }[];
  await page.goto('/#/novelas/demo-24/lectura');
  await page.locator('[data-capitulo="3"]').focus();
  await page.keyboard.press('Enter');
  const dialogo = page.getByRole('dialog');
  await expect(dialogo.locator('h2')).toHaveText(indice.find((c) => c.capitulo === 3)!.titulo);
  await expect(dialogo.locator('.q-lector__texto')).toBeVisible();
  await expect(dialogo).not.toContainText('run_id:');
  expect(aLaApi(red)).toContain('GET /novelas/demo-24/capitulos/3');
});

test('el capítulo hostil no crea nada activo ni pide nada a ejemplo.invalid (CA-26)', async ({ page, red }) => {
  await page.goto('/#/novelas/hostil-24/lectura/3');
  const texto = page.getByRole('dialog').locator('.q-lector__texto');
  await expect(texto).toContainText('<script>alert(1)</script>');
  const activos = await texto.evaluate((t) => ({
    elementos: t.querySelectorAll('script, iframe, img, a, object, embed, svg').length,
    on: [...t.querySelectorAll('*')].filter((e) => [...e.attributes].some((a) => a.name.startsWith('on'))).length,
  }));
  expect(activos).toEqual({ elementos: 0, on: 0 });
  for (const fragmento of ['<img src=x onerror=alert(1)>', '<http://ejemplo.invalid>', '[r]: javascript:alert(1)', '<svg onload=alert(1)>']) {
    await expect(texto).toContainText(fragmento);
  }
  await page.waitForLoadState('networkidle');
  expect(red.filter((p) => p.url.includes('ejemplo.invalid'))).toEqual([]);
});

test('el 8 con el checkpoint retrasado: nunca se pide; el 3, después del checkpoint (VAL-7, CA-27)', async ({ page, red }) => {
  await page.route('**/novelas/demo-24/checkpoint', async (ruta) => {
    await new Promise((r) => setTimeout(r, 3_000));
    await ruta.continue();
  });
  await page.goto('/#/novelas/demo-24/lectura/8');
  await expect(page.getByRole('dialog')).toContainText('capítulo no disponible todavía', { timeout: 10_000 });
  await page.waitForTimeout(2_000);
  expect(aLaApi(red)).not.toContain('GET /novelas/demo-24/capitulos/8');
  await page.goto('/#/novelas/demo-24/lectura/3');
  await page.reload();
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible({ timeout: 10_000 });
  const api = aLaApi(red);
  expect(api.lastIndexOf('GET /novelas/demo-24/capitulos/3')).toBeGreaterThan(api.lastIndexOf('GET /novelas/demo-24/checkpoint'));
});

test('teclado: sin dar la vuelta, Enter en un pendiente no pide nada y el foco no sale del lector (CA-28, VAL-18)', async ({
  page,
  red,
}) => {
  await page.goto('/#/novelas/demo-24/lectura');
  await page.locator('[data-capitulo="24"]').focus();
  await page.keyboard.press('ArrowRight');
  await expect(escena(page)).toHaveAttribute('data-seleccion', '24');
  await page.locator('[data-capitulo="1"]').focus();
  await page.keyboard.press('ArrowLeft');
  await expect(escena(page)).toHaveAttribute('data-seleccion', '1');
  await page.locator('[data-capitulo="9"]').focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toContainText('capítulo no disponible todavía');
  expect(aLaApi(red)).not.toContain('GET /novelas/demo-24/capitulos/9');
  await page.keyboard.press('Escape');
  await page.locator('[data-capitulo="3"]').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('[aria-current="true"]')).toHaveAttribute('data-capitulo', '4');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
  for (let i = 0; i < 20; i++) {
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => Boolean(document.activeElement?.closest('[role="dialog"]')))).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('[data-capitulo="4"]')).toBeFocused();
});

test('cámara al 4 en el fotograma siguiente con reduced motion (CA-30)', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#/novelas/demo-24/lectura');
  await expect(escena(page).locator('canvas')).toHaveCount(1);
  await page.locator('[data-capitulo="3"]').focus();
  await page.keyboard.press('ArrowRight');
  await dosFotogramas(page);
  await expect(escena(page)).toHaveAttribute('data-seleccion', '4');
  await expect(escena(page)).toHaveAttribute('data-transicion', '0');
  await expect(escena(page)).toHaveAttribute('data-camara', '4');
});

test.describe('solo Chromium', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'draw calls y WebGL desactivado se miden en Chromium');

  test('entre 1 y 5 draw calls con demo-24 y con grande-999 (RNF-03, VER-23)', async ({ page }) => {
    for (const [slug, total] of [
      ['demo-24', '24'],
      ['grande-999', '999'],
    ] as const) {
      await page.goto(`/#/novelas/${slug}/lectura`);
      await expect(escena(page)).toHaveAttribute('data-volumenes', total);
      await expect(escena(page).locator('canvas')).toHaveCount(1);
      await dosFotogramas(page);
      const llamadas = Number(await escena(page).getAttribute('data-draw-calls'));
      expect(llamadas).toBeGreaterThanOrEqual(1);
      expect(llamadas).toBeLessThanOrEqual(5);
    }
  });

  test('20 entradas y salidas sin agotar los contextos WebGL (VAL-20)', async ({ page }) => {
    const avisos: string[] = [];
    page.on('console', (m) => void (/Too many active WebGL contexts/.test(m.text()) && avisos.push(m.text())));
    for (let i = 0; i < 20; i++) {
      await page.goto('/#/novelas/demo-24/lectura');
      await expect(escena(page).locator('canvas')).toHaveCount(1);
      await page.goto('/#/novelas/demo-24/progreso');
      await expect(page.locator('canvas')).toHaveCount(0);
    }
    await page.goto('/#/novelas/demo-24/lectura');
    await expect(escena(page).locator('canvas')).toHaveCount(1);
    await dosFotogramas(page);
    await expect(escena(page)).toHaveAttribute('data-draw-calls', /^[1-5]$/);
    expect(avisos).toEqual([]);
  });
});

test.describe('sin WebGL (CA-29, VAL-19)', () => {
  test.use({ consolaPermitida: ['webgl'] });
  test.skip(({ browserName }) => browserName !== 'chromium', 'se lanza un Chromium con WebGL desactivado');

  test('«vista 3D no disponible», ningún canvas, y la lista abre y cierra el 3', async ({ baseURL }) => {
    const navegador = await chromium.launch({ args: ['--disable-webgl', '--disable-webgl2', '--disable-3d-apis'] });
    const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } });
    const errores: string[] = [];
    pagina.on('console', (m) => void (m.type() === 'error' && !/WebGL|GPU/i.test(m.text()) && errores.push(m.text())));
    pagina.on('pageerror', (e) => errores.push(e.message));
    try {
      await pagina.goto(`${baseURL}/#/novelas/demo-24/lectura`);
      await expect(pagina.getByText('vista 3D no disponible')).toBeVisible();
      await expect(pagina.locator('canvas')).toHaveCount(0);
      await pagina.locator('[data-capitulo="3"]').click();
      await expect(pagina.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
      await pagina.keyboard.press('Escape');
      await expect(pagina.getByRole('dialog')).toHaveCount(0);
      expect(errores).toEqual([]);
    } finally {
      await navegador.close();
    }
  });
});
