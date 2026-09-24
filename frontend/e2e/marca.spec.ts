// La marca en el navegador, solo en Chromium (CA-48, CA-50, CA-51, CA-53, CA-54, CA-57, CA-59;
// RNF-21, RNF-23, RNF-24): lo que jsdom no calcula —estilos computados, disposición, foco, CLS—.
import type { Page } from '@playwright/test';
import { expect, test } from './comun';

test.skip(({ browserName }) => browserName !== 'chromium', 'las medidas de la marca se toman en Chromium');

const token = (page: Page, nombre: string) =>
  page.evaluate((n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim(), nombre);
const px = (valor: string) => Number.parseFloat(valor);
const estilo = (page: Page, selector: string, propiedad: string) =>
  page.locator(selector).first().evaluate((e, p) => getComputedStyle(e).getPropertyValue(p), propiedad);
/** El color computado de un rol, en la misma forma rgb() que getComputedStyle. */
const colorDe = (page: Page, rol: string) =>
  page.evaluate((r) => {
    const sonda = document.createElement('span');
    sonda.style.color = `var(${r})`;
    document.body.append(sonda);
    const c = getComputedStyle(sonda).color;
    sonda.remove();
    return c;
  }, rol);

test('barra lateral: contenido, aria-current y estado de la API (CA-48)', async ({ page }) => {
  await page.goto('/#/novelas/demo-24/progreso');
  const barra = page.locator('.q-app__lateral');
  await expect(barra).toHaveCSS('width', '270px');
  for (const texto of ['Novelas', 'Lanzar', 'demo-24', 'Progreso', 'Lectura']) await expect(barra).toContainText(texto);
  const actuales = barra.locator('[aria-current="page"]');
  await expect(actuales).toHaveCount(1);
  await expect(actuales).toContainText('Progreso');
  await expect(actuales).toHaveCSS('background-color', await colorDe(page, '--q-nav-activo-fondo'));
  await expect(barra).toContainText('API conectada');
  await expect(barra).toContainText('http://127.0.0.1:8000');
  await page.goto('/#/');
  await expect(barra).not.toContainText('demo-24');
});

test.describe('con la API caída', () => {
  test.use({ consolaPermitida: ['caida'] });

  test('barra lateral: «API sin respuesta» (CA-48)', async ({ page }) => {
    await page.route('http://127.0.0.1:8000/**', (r) => r.abort('connectionrefused'));
    await page.goto('/#/');
    await expect(page.locator('.q-app__lateral')).toContainText('API sin respuesta');
  });
});

test('plegar y recargar: 72 px, solo iconos y nada guardado (CA-50)', async ({ page, context }) => {
  await page.goto('/#/novelas/demo-24/progreso');
  const boton = page.getByRole('button', { name: 'Plegar barra lateral' });
  await boton.click();
  const barra = page.locator('.q-app__lateral');
  await expect(barra).toHaveCSS('width', '72px');
  await expect(page.getByRole('button', { name: 'Desplegar barra lateral' })).toHaveAttribute('aria-expanded', 'false');
  // El texto queda como nombre accesible, recortado a 1 px (q-oculto-visual), no con display: none.
  for (const texto of await barra.locator('.q-nav__texto').all()) expect((await texto.boundingBox())?.width ?? 0).toBeLessThanOrEqual(1);
  for (const nombre of ['Novelas', 'Lanzar', 'Progreso', 'Lectura']) {
    await expect(barra.getByRole('link', { name: nombre })).toHaveCount(1);
  }
  await page.reload();
  await expect(barra).toHaveCSS('width', '270px');
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length + document.cookie.length)).toBe(0);
  expect(await context.cookies()).toEqual([]);
});

test('el logo: alt, tamaño, esquinas al 22 % y recortadas, desplegada y plegada (CA-51)', async ({ page }) => {
  await page.goto('/#/');
  for (const estado of ['desplegada', 'plegada']) {
    const logos = page.locator('img[src*="logo"]');
    expect(await logos.count()).toBeGreaterThan(0);
    for (const logo of await logos.all()) {
      await expect(logo).toHaveAttribute('alt', 'Qaracter');
      const lado = px(await token(page, '--q-tamano-logo'));
      const caja = await logo.boundingBox();
      expect(caja?.width).toBeCloseTo(lado, 0);
      const marco = await logo.evaluate((img) => {
        const s = getComputedStyle(img.parentElement!);
        return {
          radios: [s.borderTopLeftRadius, s.borderTopRightRadius, s.borderBottomLeftRadius, s.borderBottomRightRadius],
          overflow: s.overflow,
          clip: s.clipPath,
        };
      });
      for (const r of marco.radios) expect(px(r)).toBeCloseTo(lado * 0.22, 1);
      expect(['hidden', 'clip'].includes(marco.overflow) || marco.clip !== 'none').toBe(true);
      // La esquina superior izquierda es el fondo de la barra, no el PNG.
      const captura = await logo.screenshot();
      const esquina = await page.evaluate(async (b64) => {
        const imagen = new Image();
        imagen.src = `data:image/png;base64,${b64}`;
        await imagen.decode();
        const lienzo = new OffscreenCanvas(imagen.width, imagen.height);
        const ctx = lienzo.getContext('2d')!;
        ctx.drawImage(imagen, 0, 0);
        const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
        return `rgb(${r}, ${g}, ${b})`;
      }, captura.toString('base64'));
      expect(esquina).toBe(await colorDe(page, '--q-nav-fondo'));
    }
    if (estado === 'desplegada') await page.getByRole('button', { name: 'Plegar barra lateral' }).click();
  }
});

test('banner: display, subtítulo, un chip por campo del cursor y el texto en la mitad izquierda (CA-53)', async ({ page }) => {
  await page.goto('/#/novelas/demo-24/progreso');
  const banner = page.locator('.q-banner');
  await expect(banner.locator('.q-banner__titular')).toHaveText('demo-24');
  expect(await estilo(page, '.q-banner__titular', 'font-family')).toContain('Outfit');
  await expect(banner.locator('.q-banner__subtitulo')).toContainText('24 CAPÍTULOS');
  await expect(banner.locator('.q-chip')).toHaveCount(4);
  const [caja, texto] = await Promise.all([banner.boundingBox(), banner.locator('.q-banner__texto').boundingBox()]);
  expect(texto!.x + texto!.width).toBeLessThanOrEqual(caja!.x + caja!.width / 2);
});

test('rejilla de dos columnas a 1440 px y una a 1024, sin desplazamiento horizontal (CA-54)', async ({ page }) => {
  await page.goto('/#/novelas/demo-24/progreso');
  await expect(page.locator('.q-tension').first()).toBeVisible();
  const columnas = () => estilo(page, '.q-rejilla', 'grid-template-columns').then((v) => v.split(' ').length);
  const desborda = () => page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  const metricas = await page.locator('.q-metricas > *').evaluateAll((ms) => new Set(ms.map((m) => m.getBoundingClientRect().top)).size);
  expect(metricas).toBe(1);
  expect(await columnas()).toBe(2);
  expect(await desborda()).toBe(false);
  await page.setViewportSize({ width: 1024, height: 900 });
  expect(await columnas()).toBe(1);
  expect(await desborda()).toBe(false);
});

test('ningún elemento de la plataforma que no aplica, lang="es" y color-scheme: light (CA-59)', async ({ page }) => {
  for (const ruta of ['/#/', '/#/lanzar', '/#/novelas/demo-24/progreso', '/#/novelas/demo-24/lectura']) {
    await page.goto(ruta);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[role="switch"]')).toHaveCount(0);
    const nombres = await page.locator('button, a, [role], img, input, select').evaluateAll((es) =>
      es.map((e) => `${e.getAttribute('aria-label') ?? ''} ${e.getAttribute('alt') ?? ''} ${e.textContent ?? ''}`.toLowerCase()),
    );
    expect(nombres.filter((n) => /avatar|notificaci|bienvenid|modo oscuro|idioma|language/.test(n))).toEqual([]);
    await expect(page.locator('html')).toHaveAttribute('lang', 'es');
    expect(await estilo(page, 'html', 'color-scheme')).toBe('light');
  }
});

test('las medidas computadas son las de sus tokens (RNF-23)', async ({ page }) => {
  await page.goto('/#/novelas/demo-24/progreso');
  await expect(page.locator('.q-metrica__valor').first()).not.toBeEmpty();
  const medidas: [string, string, string][] = [
    ['.q-app__lateral', 'width', '--q-ancho-barra'],
    ['.q-contenido', 'padding-left', '--q-margen-contenido'],
    ['.q-rejilla', 'column-gap', '--q-hueco'],
    ['.q-rejilla > .q-tarjeta', 'padding-top', '--q-relleno-tarjeta'],
    ['.q-rejilla > .q-tarjeta', 'border-top-left-radius', '--q-radio-tarjeta'],
    ['.q-banner', 'border-top-left-radius', '--q-radio-tarjeta'],
    ['.q-nav__item', 'border-top-left-radius', '--q-radio-control'],
    ['.q-barra__titulo', 'font-size', '--q-texto-titulo-pagina'],
    ['.q-tarjeta__titulo', 'font-size', '--q-texto-titulo-tarjeta'],
    ['body', 'font-size', '--q-texto-cuerpo'],
    ['.q-etiqueta', 'font-size', '--q-texto-etiqueta'],
    ['.q-metrica__valor', 'font-size', '--q-texto-metrica'],
    ['.q-banner__titular', 'font-size', '--q-texto-banner'],
    ['.q-banner__subtitulo', 'font-size', '--q-texto-banner-subtitulo'],
    ['.q-cuadro-icono', 'width', '--q-cuadro-icono'],
    ['.q-icono', 'width', '--q-tamano-icono'],
  ];
  const distintas: string[] = [];
  for (const [selector, propiedad, nombre] of medidas) {
    const [computado, esperado] = [px(await estilo(page, selector, propiedad)), px(await token(page, nombre))];
    if (Math.abs(computado - esperado) > 0.01) distintas.push(`${selector} ${propiedad}: ${computado} ≠ ${nombre} ${esperado}`);
  }
  expect(distintas).toEqual([]);
  const pesos: [string, string][] = [
    ['.q-barra__titulo', '--q-peso-titulo-pagina'],
    ['.q-tarjeta__titulo', '--q-peso-titulo-tarjeta'],
    ['.q-metrica__valor', '--q-peso-metrica'],
    ['.q-banner__titular', '--q-peso-banner'],
  ];
  for (const [selector, nombre] of pesos) expect(await estilo(page, selector, 'font-weight')).toBe(await token(page, nombre));
});

test('Tab por todos los interactivos con un outline de ≥ 2 px en el color de foco (RNF-24)', async ({ page }) => {
  for (const ruta of ['/#/', '/#/lanzar', '/#/novelas/demo-24/progreso', '/#/novelas/demo-24/lectura']) {
    await page.goto('about:blank'); // carga en frío: sin marcas ni foco de la vista anterior
    await page.goto(ruta);
    await page.waitForLoadState('networkidle');
    const colores = await Promise.all(['--q-foco', '--q-foco-sobre-oscuro'].map((r) => colorDe(page, r)));
    let vistos = 0;
    const fallos: string[] = [];
    for (let i = 0; i < 80; i++) {
      await page.keyboard.press('Tab');
      // Cada elemento se marca al visitarlo: el recorrido acaba al volver a uno ya visto.
      const foco = await page.evaluate(() => {
        const e = document.activeElement as HTMLElement | null;
        if (!e || e === document.body || e.dataset.e2eVisto) return null;
        e.dataset.e2eVisto = '1';
        const s = getComputedStyle(e);
        return { id: `${e.tagName}.${e.className}:${e.textContent?.slice(0, 20)}`, ancho: s.outlineWidth, estilo: s.outlineStyle, color: s.outlineColor };
      });
      if (!foco) break;
      vistos++;
      if (foco.estilo === 'none' || Number.parseFloat(foco.ancho) < 2 || !colores.includes(foco.color)) fallos.push(`${foco.id} ${foco.ancho} ${foco.color}`);
    }
    expect(vistos).toBeGreaterThan(2);
    expect(fallos, ruta).toEqual([]);
  }
});

test('CLS ≤ 0,1 en cada vista hasta los primeros datos (RNF-21)', async ({ page }) => {
  for (const [ruta, listo] of [
    ['/#/', '.q-entrada'],
    ['/#/lanzar', '.q-lanzar__slugs .q-etiqueta'],
    ['/#/novelas/demo-24/progreso', '.q-tension'],
    ['/#/novelas/demo-24/lectura', '.q-volumen'],
  ] as const) {
    await page.goto('about:blank');
    await page.addInitScript(() => {
      (window as unknown as { cls: number }).cls = 0;
      new PerformanceObserver((lista) => {
        for (const e of lista.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[]) {
          if (!e.hadRecentInput) (window as unknown as { cls: number }).cls += e.value;
        }
      }).observe({ type: 'layout-shift', buffered: true });
    });
    await page.goto(ruta);
    await expect(page.locator(listo).first()).toBeVisible();
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => (window as unknown as { cls: number }).cls), ruta).toBeLessThanOrEqual(0.1);
  }
});

test('foco visible con forced-colors y transiciones a 0 s con reduced motion (CA-57)', async ({ page }) => {
  await page.emulateMedia({ forcedColors: 'active' });
  await page.goto('/#/lanzar');
  await page.getByRole('button', { name: 'Generar orden' }).focus();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => getComputedStyle(document.activeElement!).outlineStyle)).not.toBe('none');
  expect(px(await page.evaluate(() => getComputedStyle(document.activeElement!).outlineWidth))).toBeGreaterThanOrEqual(2);
  await page.emulateMedia({ forcedColors: 'none', reducedMotion: 'reduce' });
  await page.reload();
  for (const selector of ['.q-boton', '.q-nav__item', '.q-campo__control']) {
    expect(await estilo(page, selector, 'transition-duration'), selector).toMatch(/^0s(, 0s)*$/);
  }
});
