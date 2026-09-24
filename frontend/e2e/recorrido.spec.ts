// El recorrido del panel contra la API real: Inicio, Lanzar, Progreso y Lectura, con la red, el
// almacenamiento y la consola vigilados (CA-08, CA-10, CA-16, CA-19; RNF-05, RNF-06, RNF-08,
// RNF-09; CA-56 y CA-61 en su parte e2e).
import { aLaApi, API, expect, lanzamientoSimulado, PANEL, test } from './comun';

test('Inicio: una entrada por novela con su cursor y sus enlaces (CA-08)', async ({ page, request }) => {
  const novelas = (await (await request.get(`${API}/novelas`)).json()) as { slug: string }[];
  await page.goto('/#/');
  const entradas = page.locator('.q-entrada');
  await expect(entradas).toHaveCount(novelas.length);
  for (const slug of ['demo-24', 'recien-creada']) {
    const entrada = entradas.filter({ has: page.getByText(slug, { exact: true }) });
    await expect(entrada).toContainText('capítulo');
    await expect(entrada).toContainText('fase');
    await expect(entrada).toContainText('último paso');
    await expect(entrada.locator(`a[href="#/novelas/${slug}/progreso"]`).first()).toBeVisible();
    await expect(entrada.locator(`a[href="#/novelas/${slug}/lectura"]`)).toBeVisible();
  }
  await expect(page.locator('a[href="#/lanzar"]').first()).toBeVisible();
});

test('recarga con /lectura/3 reabre el capítulo 3 (CA-10)', async ({ page }) => {
  await page.goto('/#/novelas/demo-24/lectura');
  await page.locator('[data-capitulo="3"]').click();
  await expect(page).toHaveURL(/#\/novelas\/demo-24\/lectura\/3$/);
  await expect(page.getByRole('dialog')).toContainText('Capítulo 3');
  await page.reload();
  await expect(page).toHaveURL(/#\/novelas\/demo-24\/lectura\/3$/);
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toContainText('Capítulo 3');
});

test('Lanzar: un clic lo envía al backend, sin órdenes que copiar ni descargas (CA-16)', async ({ page, red }) => {
  const descargas: string[] = [];
  page.on('download', (d) => descargas.push(d.suggestedFilename()));
  await lanzamientoSimulado(page);
  await page.goto('/#/lanzar');
  await expect(page.getByText('todavía no se ha lanzado ninguna novela desde el panel')).toBeVisible();
  await page.getByRole('textbox', { name: 'Slug' }).fill('nueva-prueba');
  await page.getByRole('textbox', { name: 'Idea' }).fill('Un faro apagado.');
  await page.getByLabel('Capítulos (opcional)').fill('3');
  await page.getByLabel('Palabras totales (opcional)').fill('9000');
  await page.getByRole('button', { name: 'Lanzar novela' }).click();
  await expect(page.locator('.q-lanzar__resultado-envio')).toContainText('nueva-prueba: lanzada');
  await expect(page.locator('.q-lanzamiento').first()).toContainText('en marcha');
  await expect(page.getByRole('button', { name: /^Copiar/ })).toHaveCount(0);
  expect(descargas).toEqual([]);
  expect(new Set(aLaApi(red))).toEqual(new Set(['GET /novelas', 'GET /lanzamientos', 'POST /lanzamientos']));
});

test('recien-creada: tensión sin escaleta y sin aviso de error (CA-19)', async ({ page }) => {
  await page.goto('/#/novelas/recien-creada/progreso');
  await expect(page.getByText('el plan todavía no tiene escaleta')).toBeVisible();
  await expect(page.locator('.q-tension__objetivo')).toHaveCount(0);
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByText('sin runs todavía').first()).toBeVisible();
});

test('red, almacenamiento, fuentes y favicon en un recorrido completo (RNF-06, RNF-08, RNF-09, CA-56, CA-61)', async ({
  page,
  red,
  context,
}) => {
  const fuentes: string[] = [];
  page.on('response', (r) => void (r.request().resourceType() === 'font' && fuentes.push(r.url())));
  for (const ruta of ['/#/', '/#/lanzar', '/#/novelas/demo-24/progreso', '/#/novelas/demo-24/lectura/3']) {
    await page.goto(ruta);
    await page.waitForLoadState('networkidle');
  }
  await page.locator('link[rel="icon"]').evaluate(async (l: HTMLLinkElement) => void (await fetch(l.href)));
  // Control positivo: el espía ve lo que tiene que ver.
  expect(red.some((p) => p.url === `${API}/novelas`)).toBe(true);
  expect(red.some((p) => p.url === `${PANEL}/favicon.png`)).toBe(true);
  expect(fuentes.length).toBeGreaterThan(0);
  for (const f of fuentes) expect(f).toMatch(new RegExp(`^${PANEL}/.+\\.woff2$`));
  // RNF-06 y RNF-08.
  expect(red.filter((p) => p.metodo !== 'GET')).toEqual([]);
  expect(red.filter((p) => !p.url.startsWith(PANEL) && !p.url.startsWith(API) && !p.url.startsWith('data:'))).toEqual([]);
  // RNF-09.
  const almacen = await page.evaluate(async () => ({
    local: localStorage.length,
    sesion: sessionStorage.length,
    bases: (await indexedDB.databases?.())?.length ?? 0,
    cookies: document.cookie,
  }));
  expect(almacen).toEqual({ local: 0, sesion: 0, bases: 0, cookies: '' });
  expect(await context.cookies()).toEqual([]);
});

test('Progreso hace ≤ 60 peticiones por minuto y nada propio del estado de la API (RNF-05, D50)', async ({ page, red }) => {
  await page.clock.install();
  await page.goto('/#/novelas/demo-24/progreso');
  await expect(page.locator('.q-metrica__valor').first()).not.toBeEmpty();
  const antes = aLaApi(red).length;
  for (let s = 0; s < 60; s++) {
    await page.clock.runFor(1_000);
    await page.waitForTimeout(5); // deja salir las peticiones de la ronda
  }
  await page.waitForLoadState('networkidle');
  const minuto = aLaApi(red).slice(antes);
  expect(minuto.length).toBeGreaterThan(0);
  expect(minuto.length).toBeLessThanOrEqual(60);
  expect(minuto.every((p) => /^GET \/novelas\/demo-24\/(estado|config|escaleta|checkpoint|capitulos|runs)/.test(p))).toBe(true);
});
