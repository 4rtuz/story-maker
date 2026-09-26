// Lo común a todos los e2e: un espía de cada petición del contexto, registrado antes de la primera
// navegación, y la escucha de console.error y pageerror (RNF-16, D54), que falla el test al final.
import { test as base, expect, type ConsoleMessage, type Page } from '@playwright/test';

export { expect };

export const API = 'http://127.0.0.1:8000';
export const PANEL = 'http://localhost:5173';

export interface Peticion {
  url: string;
  metodo: string;
}

/**
 * Los mensajes que el navegador emite por un fallo esperado, no del código del panel. D54 fija la
 * lista cerrada: logo.png que no carga y la fuente display retrasada o fallida, que cada escenario
 * activa con `consolaPermitida`, más la caída de la API que provoca a propósito resiliencia.spec.ts,
 * que tampoco es un fallo del panel; WebGL salió con la estantería 3D (spec 0015, RF-12). Se añade el
 * 404 de `…/escaleta` de una novela sin plan, que RF-19 trata como respuesta correcta (D45) y Chromium
 * registra igualmente como «Failed to load resource»: el mensaje es del navegador y el panel no puede
 * evitarlo. Lo mismo el de `…/portada` y `…/metricas` (spec 0015, §5.4): los workspaces sintéticos no
 * tienen portada ni métricas, y el panel responde con la cubierta tipográfica y el estado vacío.
 */
const RECURSO_AUSENTE = (m: ConsoleMessage): boolean =>
  /status of 404/.test(m.text()) && /\/novelas\/[a-z0-9-]+\/(escaleta|portada|metricas)$/.test(m.location().url);

export const EXCLUSIONES = {
  logo: (m: ConsoleMessage) => /logo[^/]*\.png/.test(m.location().url) || /logo[^/]*\.png/.test(m.text()),
  fuente: (m: ConsoleMessage) => /\.woff2/.test(m.location().url) || /downloadable font|\.woff2/i.test(m.text()),
  /** Las caídas de la API que provoca resiliencia.spec.ts con page.route (CA-04, RNF-15). */
  caida: (m: ConsoleMessage) => /^Failed to load resource/.test(m.text()) && m.location().url.startsWith(API),
} as const;

export const test = base.extend<{
  red: Peticion[];
  consolaPermitida: (keyof typeof EXCLUSIONES)[];
  errores: string[];
}>({
  consolaPermitida: [[], { option: true }],
  red: async ({ context }, use) => {
    const vistas: Peticion[] = [];
    context.on('request', (r) => vistas.push({ url: r.url(), metodo: r.method() }));
    await use(vistas);
  },
  errores: [
    async ({ page, consolaPermitida }, use) => {
      const errores: string[] = [];
      page.on('console', (m) => {
        if (m.type() !== 'error' || RECURSO_AUSENTE(m)) return;
        if (consolaPermitida.some((clave) => EXCLUSIONES[clave](m))) return;
        errores.push(`console.error: ${m.text()} (${m.location().url})`);
      });
      page.on('pageerror', (e) => errores.push(`pageerror: ${e.message}`));
      await use(errores);
      expect(errores, 'console.error o pageerror durante el test (RNF-16)').toEqual([]);
    },
    { auto: true },
  ],
});

/** Las peticiones a la API, como `GET /novelas/demo-24/estado`. */
export const aLaApi = (red: Peticion[]): string[] =>
  red.filter((p) => p.url.startsWith(API)).map((p) => `${p.metodo} ${p.url.slice(API.length)}`);

/** POST /lanzamientos respondido en el navegador: con `reuseExistingServer`, la API podría ser la
 * del operador sobre las novelas de verdad, y un e2e no lanza nunca `claude`. */
export async function lanzamientoSimulado(page: Page): Promise<void> {
  await page.route(`${API}/lanzamientos`, (ruta) =>
    ruta.request().method() === 'POST'
      ? ruta.fulfill({
          status: 202,
          contentType: 'application/json',
          body: JSON.stringify({
            slug: 'nueva-prueba',
            estado: 'en_marcha',
            paso: 'entorno',
            detalle: 'arrancando',
            actualizado: '2026-09-24T10:00:00Z',
            detener_pedido: false,
            registro: [],
          }),
        })
      : ruta.fallback(),
  );
}
