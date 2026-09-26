// RNF-15 y CA-04 en su parte e2e: la API cae 60 s y vuelve. page.route solo hace fallar o retrasa
// respuestas reales; no inventa datos.
import { expect, test } from './comun';

test.use({ consolaPermitida: ['caida'] });

test('caída de 60 s: aviso con los datos conservados y, al volver, datos nuevos en ≤ 1 ronda (RNF-15, CA-04)', async ({
  page,
}) => {
  await page.clock.install();
  await page.goto('/#/novelas/demo-24/progreso');
  await expect(page.getByText('de 24 capítulos')).toBeVisible();
  await expect(page.getByText('API conectada')).toBeVisible();

  await page.route('http://127.0.0.1:8000/**', (ruta) => ruta.abort('connectionrefused'));
  await page.clock.runFor(10_000);
  await expect(page.getByRole('alert')).toContainText('API no disponible en http://127.0.0.1:8000');
  await expect(page.getByText('de 24 capítulos')).toBeVisible(); // lo anterior sigue
  await expect(page.getByText('API sin respuesta')).toBeVisible();
  await page.clock.runFor(50_000);
  await expect(page.getByText('de 24 capítulos')).toBeVisible();

  // Las rondas de la caída terminan antes de que vuelva la API: RNF-15 cuenta desde ahí.
  await page.waitForLoadState('networkidle');
  await page.unroute('http://127.0.0.1:8000/**');
  const actualizado = page.locator('.q-barra__actualizado');
  const antes = await actualizado.textContent();
  await page.clock.runFor(10_000); // una ronda
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByText('API conectada')).toBeVisible();
  await expect(actualizado).not.toHaveText(antes ?? '');
});

test('un 404 de estado muestra su detail y conserva el cursor (CA-04)', async ({ page }) => {
  await page.clock.install();
  await page.goto('/#/novelas/demo-24/progreso');
  await expect(page.getByText('de 24 capítulos')).toBeVisible();
  await page.route('**/novelas/demo-24/estado', (ruta) =>
    ruta.fulfill({ status: 404, contentType: 'application/json', body: '{"detail": "no existe la novela demo-24"}' }),
  );
  await page.clock.runFor(10_000);
  await expect(page.getByRole('alert')).toHaveText('no existe la novela demo-24');
  await expect(page.getByText('de 24 capítulos')).toBeVisible();
});
