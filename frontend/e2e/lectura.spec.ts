// Lectura en el navegador: portada e índice sin estantería 3D, lector, capítulo hostil, teclado y
// foco atrapado (CA-25, CA-26, CA-28; VAL-7, VAL-18; spec 0015 §5.5 y RF-12).
import type { Page } from '@playwright/test';
import { aLaApi, API, expect, test } from './comun';

const enlaceDelIndice = (page: Page, n: number) => page.locator(`[data-testid="indice-capitulo"][data-destino="${n}"]`);

test('portada con título legible, un enlace por capítulo cerrado y ni canvas ni three.js (spec 0015, RF-12)', async ({
  page,
  red,
}) => {
  await page.goto('/#/novelas/demo-24/lectura');
  const portada = page.locator('[data-testid="portada"]');
  // La API sirve el slug como título: el panel enseña el slug legible (tituloDe, portada.ts).
  await expect(portada.locator('[data-testid="portada-titulo"]')).toHaveText('Demo 24');
  await expect(portada.locator('.q-portada')).toBeVisible();
  await expect(page.locator('[data-testid="indice-capitulo"]')).toHaveCount(7);
  await portada.getByRole('link', { name: 'Empezar a leer' }).click();
  await expect(page).toHaveURL(/#\/novelas\/demo-24\/lectura\/1$/);
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
  expect(red.filter((p) => /three/i.test(p.url))).toEqual([]);
});

test('abrir el 3 pide su texto y muestra el título del índice sin frontmatter (CA-25)', async ({ page, red, request }) => {
  const indice = (await (await request.get(`${API}/novelas/demo-24/capitulos`)).json()) as { capitulo: number; titulo: string }[];
  await page.goto('/#/novelas/demo-24/lectura');
  await enlaceDelIndice(page, 3).focus();
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

test('teclado: sin pasar del último cerrado, un pendiente no pide nada y el foco no sale del lector (CA-28, VAL-18)', async ({
  page,
  red,
}) => {
  await page.goto('/#/novelas/demo-24/lectura');
  await enlaceDelIndice(page, 7).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
  await page.keyboard.press('ArrowRight'); // el 8 está en curso: → no lleva a él
  await expect(page).toHaveURL(/lectura\/7$/);
  await page.keyboard.press('Escape');
  await page.goto('/#/novelas/demo-24/lectura/9');
  await expect(page.getByRole('dialog')).toContainText('capítulo no disponible todavía');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  expect(aLaApi(red).filter((p) => /capitulos\/(8|9)$/.test(p))).toEqual([]);
  await enlaceDelIndice(page, 3).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
  await page.keyboard.press('ArrowRight');
  await expect(page).toHaveURL(/lectura\/4$/);
  await expect(page.getByRole('dialog').locator('.q-lector__capitulo')).toHaveText('Capítulo 4');
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
  for (let i = 0; i < 20; i++) {
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => Boolean(document.activeElement?.closest('[role="dialog"]')))).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(enlaceDelIndice(page, 3)).toBeFocused(); // vuelve al enlace que lo abrió
});
