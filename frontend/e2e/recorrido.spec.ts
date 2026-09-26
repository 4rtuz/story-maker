// El recorrido del panel contra la API real: Inicio, Lanzar, Progreso y Lectura, con la red, el
// almacenamiento y la consola vigilados (CA-08, CA-10, CA-16, CA-19; RNF-05, RNF-06, RNF-08,
// RNF-09; CA-56 y CA-61 en su parte e2e; spec 0015 RF-08 a RF-11).
import { aLaApi, API, expect, lanzamientoSimulado, PANEL, test } from './comun';

/** Las novelas que el inicio no enseña (spec 0015, RF-08): la misma regla que src/shared/visibles.ts. */
const visible = (slug: string): boolean => !/^(eval|humo)-/.test(slug) && slug !== 'regalo-carmen';

test('Inicio: una portada por novela visible con su estado, su avance y sus enlaces (CA-08, spec 0015 §5.5)', async ({
  page,
  request,
}) => {
  const novelas = (await (await request.get(`${API}/novelas`)).json()) as { slug: string }[];
  await page.goto('/#/');
  const obras = page.locator('.q-estanteria .q-obra[data-slug]');
  await expect(obras).toHaveCount(novelas.filter((n) => visible(n.slug)).length);
  for (const [slug, titulo] of [
    ['demo-24', 'Demo 24'],
    ['recien-creada', 'Recien creada'],
  ] as const) {
    const obra = page.locator(`.q-obra[data-slug="${slug}"]`);
    await expect(obra.locator('.q-portada')).toContainText(titulo);
    await expect(obra.locator('.q-estado')).not.toBeEmpty();
    await expect(obra.getByRole('progressbar')).toHaveAttribute('aria-valuenow', /^\d+$/);
    await expect(obra.getByRole('link', { name: 'Leer', exact: true })).toHaveAttribute('href', `#/novelas/${slug}/lectura`);
    await expect(obra.getByRole('link', { name: 'Progreso', exact: true })).toHaveAttribute('href', `#/novelas/${slug}/progreso`);
  }
  await expect(page.locator('.q-obra--nueva')).toHaveAttribute('href', '#/lanzar');
});

test('Inicio: sin eval-*, humo-* ni regalo-carmen, y sin pedir nada de ellas (spec 0015, RF-08)', async ({ page, red }) => {
  const ocultas = ['eval-rubrica', 'humo-3', 'regalo-carmen'];
  await page.route(`${API}/novelas`, async (ruta) => {
    const reales = (await (await ruta.fetch()).json()) as { slug: string }[];
    const copia = reales.find((n) => n.slug === 'demo-24')!;
    await ruta.fulfill({ json: [...reales, ...ocultas.map((slug) => ({ ...copia, slug }))] });
  });
  await page.goto('/#/');
  await expect(page.locator('.q-obra[data-slug="demo-24"]')).toBeVisible();
  await page.waitForLoadState('networkidle');
  for (const slug of ocultas) await expect(page.locator(`.q-obra[data-slug="${slug}"]`)).toHaveCount(0);
  expect(aLaApi(red).filter((p) => ocultas.some((slug) => p.includes(`/novelas/${slug}/`)))).toEqual([]);
});

test('recarga con /lectura/3 reabre el capítulo 3 (CA-10)', async ({ page }) => {
  await page.goto('/#/novelas/demo-24/lectura');
  await page.locator('[data-testid="indice-capitulo"][data-destino="3"]').click();
  await expect(page).toHaveURL(/#\/novelas\/demo-24\/lectura\/3$/);
  await expect(page.getByRole('dialog')).toContainText('Capítulo 3');
  await page.reload();
  await expect(page).toHaveURL(/#\/novelas\/demo-24\/lectura\/3$/);
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toContainText('Capítulo 3');
});

test('Lanzar: el chat pregunta y un clic lo envía al backend, sin órdenes que copiar ni descargas (CA-16, spec 0015 RF-09, RF-10)', async ({
  page,
  red,
}) => {
  const descargas: string[] = [];
  page.on('download', (d) => descargas.push(d.suggestedFilename()));
  await lanzamientoSimulado(page);
  await page.goto('/#/lanzar');
  await expect(page.locator('.q-tablero [data-columna]')).toHaveCount(4);
  const chat = page.locator('.q-chat');
  await expect(chat.getByRole('log')).toBeVisible();
  const respuesta = chat.getByRole('textbox', { name: 'Tu respuesta' });
  // Cada pregunta llega tras la pausa del asistente: fill y click esperan a que se vea.
  const responder = async (texto: string) => {
    await respuesta.fill(texto);
    await respuesta.press('Enter');
  };
  await chat.getByRole('button', { name: 'No, es para mí' }).click();
  await responder('Un faro apagado.');
  await chat.getByRole('button', { name: 'Noir' }).click();
  await expect(chat.locator('.q-burbuja--bot').last()).toHaveText('¿Y el tono?');
  await chat.getByRole('button', { name: 'Omitir' }).click();
  await responder('3');
  await responder('9000');
  await expect(chat.getByRole('button', { name: 'faro-apagado' })).toBeVisible(); // la sugerencia del nombre corto
  await responder('nueva-prueba');
  const resumen = chat.locator('.q-resumen');
  await expect(resumen).toContainText('Noir');
  await expect(resumen).toContainText('nueva-prueba');
  await expect(resumen).not.toContainText('Extensión'); // RF-09: no pregunta la extensión
  await chat.getByRole('button', { name: 'Lanzar novela' }).click();
  await expect(page.locator('[data-columna="proceso"] .q-tarea')).toContainText('Nueva prueba');
  await expect(chat.locator('.q-burbuja--bot').last()).toContainText('¡En marcha!');
  await expect(page.getByRole('button', { name: /^Copiar/ })).toHaveCount(0);
  expect(descargas).toEqual([]);
  // Las portadas de las tarjetas son <img> perezosos: se pidan o no, no son órdenes.
  expect(new Set(aLaApi(red).filter((p) => !p.endsWith('/portada')))).toEqual(
    new Set(['GET /novelas', 'GET /lanzamientos', 'POST /lanzamientos']),
  );
});

test('recien-creada: tensión sin escaleta y sin aviso de error (CA-19)', async ({ page }) => {
  await page.goto('/#/novelas/recien-creada/progreso');
  await expect(page.getByText('el plan todavía no tiene escaleta')).toBeVisible();
  await expect(page.locator('.q-tension__objetivo')).toHaveCount(0);
  await expect(page.getByText('Todavía no hay métricas de Langfuse')).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('Progreso: ficha, cuatro cifras y el hito en curso con un lanzamiento en marcha (spec 0015, RF-11)', async ({ page }) => {
  await page.route(`${API}/lanzamientos`, (ruta) =>
    ruta.request().method() === 'GET'
      ? ruta.fulfill({
          json: [
            {
              slug: 'demo-24',
              estado: 'en_marcha',
              paso: 'capitulo 08',
              detalle: 'escribiendo',
              actualizado: '2026-09-24T10:00:00Z',
              detener_pedido: false,
              registro: [],
            },
          ],
        })
      : ruta.fallback(),
  );
  await page.goto('/#/novelas/demo-24/progreso');
  await expect(page.locator('.q-ficha__titulo')).toHaveText('Demo 24');
  await expect(page.locator('.q-metrica')).toHaveCount(4);
  await expect(page.getByText('de 24 capítulos')).toBeVisible();
  const creacion = page.getByRole('region', { name: 'Proceso de creación' });
  await expect(creacion.locator('.q-hitos .q-hito[aria-current="step"]')).toHaveCount(1);
  await expect(creacion.locator('.q-hito', { hasText: 'Capítulo 7 aceptado' })).toHaveCount(1);
  await expect(creacion.getByRole('progressbar', { name: 'Avance de la novela' })).toHaveAttribute('aria-valuenow', /^[1-9]\d?$/);
  await expect(page.getByRole('region', { name: 'Métricas de Langfuse' })).toBeVisible();
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
  // Seis recursos cada 10 s y /lanzamientos cada 3 s (spec 0015): 36 + 20 = 56 por minuto, más la
  // portada si su <img> sale después de la primera ronda.
  const antes = aLaApi(red).length;
  for (let s = 0; s < 60; s++) {
    await page.clock.runFor(1_000);
    await page.waitForTimeout(5); // deja salir las peticiones de la ronda
  }
  await page.waitForLoadState('networkidle');
  const minuto = aLaApi(red).slice(antes);
  expect(minuto.length).toBeGreaterThan(0);
  expect(minuto.length).toBeLessThanOrEqual(60);
  expect(minuto.filter((p) => !/^GET \/(novelas\/demo-24\/(estado|config|escaleta|checkpoint|libro|metricas|portada)|lanzamientos)$/.test(p))).toEqual([]);
});
