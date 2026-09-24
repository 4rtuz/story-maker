// Regresión visual (RNF-22, CA-53, CA-57, CA-58): una captura por vista y estado y por componente y
// estado, en Chromium a 1440 × 900, con el reloj fijo y el canvas y las horas enmascarados. Las
// referencias son las de la imagen de Playwright del job frontend-e2e (D30): en otra plataforma el
// renderizado de fuentes difiere y el test se salta. Solo muestran workspaces sintéticos (RF-60).
import type { Page } from '@playwright/test';
import { expect, test } from './comun';

// VISUAL_LOCAL=1 lo ejecuta en otra plataforma para depurar el propio spec; sus capturas no valen
// como referencia y no se versionan.
const PLATAFORMA = process.platform === 'linux' || process.env.VISUAL_LOCAL === '1';
test.skip(({ browserName }) => browserName !== 'chromium' || !PLATAFORMA, 'referencias de la imagen de Playwright del CI');
test.use({ consolaPermitida: ['caida'] });

const API = 'http://127.0.0.1:8000/**';
const MOMENTO = new Date('2026-09-24T10:00:00+02:00');

async function preparar(page: Page): Promise<void> {
  await page.clock.setFixedTime(MOMENTO);
}

const capturar = (page: Page, nombre: string) =>
  expect(page).toHaveScreenshot(`${nombre}.png`, {
    fullPage: true,
    maxDiffPixelRatio: 0.001,
    animations: 'disabled',
    mask: [page.locator('canvas'), page.locator('.q-barra__actualizado, time, .q-fecha')],
  });

const VISTAS: [string, string, string][] = [
  ['inicio', '/#/', '.q-entrada'],
  ['lanzar', '/#/lanzar', '.q-lanzar__slugs .q-etiqueta'],
  ['progreso', '/#/novelas/demo-24/progreso', '.q-tension'],
  ['lectura', '/#/novelas/demo-24/lectura', '.q-volumen'],
];

for (const [nombre, ruta, listo] of VISTAS) {
  test(`${nombre}: datos`, async ({ page }) => {
    await preparar(page);
    await page.goto(ruta);
    await expect(page.locator(listo).first()).toBeVisible();
    await page.waitForLoadState('networkidle');
    await capturar(page, `${nombre}-datos`);
  });

  test(`${nombre}: carga`, async ({ page }) => {
    await preparar(page);
    await page.route(API, () => {}); // sin responder: el esqueleto se queda
    await page.goto(ruta);
    await page.waitForTimeout(300);
    await capturar(page, `${nombre}-carga`);
  });

  test(`${nombre}: error`, async ({ page }) => {
    await preparar(page);
    await page.route(API, (r) => r.abort('connectionrefused'));
    await page.goto(ruta);
    await expect(page.getByText('API sin respuesta')).toBeVisible();
    await capturar(page, `${nombre}-error`);
  });
}

test('inicio: vacío', async ({ page }) => {
  await preparar(page);
  await page.route('http://127.0.0.1:8000/novelas', (r) => r.fulfill({ json: [] }));
  await page.goto('/#/');
  await expect(page.getByText('todavía no hay novelas: lanza la primera')).toBeVisible();
  await capturar(page, 'inicio-vacio');
});

for (const vista of ['progreso', 'lectura']) {
  test(`${vista}: vacío con recien-creada`, async ({ page }) => {
    await preparar(page);
    await page.goto(`/#/novelas/recien-creada/${vista}`);
    await page.waitForLoadState('networkidle');
    await capturar(page, `${vista}-vacio`);
  });
}

test('lector abierto', async ({ page }) => {
  await preparar(page);
  await page.goto('/#/novelas/demo-24/lectura/3');
  await expect(page.locator('.q-lector__texto')).toBeVisible();
  await capturar(page, 'lector');
});

test('banner (CA-53)', async ({ page }) => {
  await preparar(page);
  await page.goto('/#/novelas/demo-24/progreso');
  await expect(page.locator('.q-banner .q-chip')).toHaveCount(4);
  await expect(page.locator('.q-banner')).toHaveScreenshot('banner.png', { maxDiffPixelRatio: 0.001 });
});

const COMPONENTES: [string, string, string][] = [
  ['boton-primario', '/#/lanzar', 'button.q-boton--primario'],
  ['boton-secundario', '/#/novelas/demo-24/lectura/3', '.q-lector button.q-boton--secundario'],
  ['campo', '/#/lanzar', '#lanzar-slug'],
  ['nav-item', '/#/', '.q-nav__item >> nth=1'],
  ['plegar', '/#/', '.q-plegar'],
  ['entrada', '/#/', '.q-entrada__slug >> nth=0'],
  ['volumen', '/#/novelas/demo-24/lectura', '.q-volumen >> nth=4'],
  ['detalles', '/#/novelas/demo-24/progreso', '.q-detalles__resumen'],
];

for (const [nombre, ruta, selector] of COMPONENTES) {
  // Sin estado deshabilitado: los botones solo se deshabilitan mientras dura su petición.
  for (const estado of ['reposo', 'hover', 'foco'] as const) {
    test(`${nombre}: ${estado} (CA-57)`, async ({ page }) => {
      await preparar(page);
      await page.goto(ruta);
      const elemento = page.locator(selector);
      await expect(elemento).toBeVisible();
      await page.waitForLoadState('networkidle');
      if (estado === 'hover') await elemento.hover();
      if (estado === 'foco') {
        await elemento.focus();
        await page.keyboard.press('Shift+Tab');
        await page.keyboard.press('Tab'); // foco de teclado: :focus-visible
      }
      await expect(elemento).toHaveScreenshot(`${nombre}-${estado}.png`, { maxDiffPixelRatio: 0.001, animations: 'disabled' });
    });
  }
}
