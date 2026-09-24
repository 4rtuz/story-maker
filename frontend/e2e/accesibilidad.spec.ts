// RNF-12 y RNF-13 (D12): axe con WCAG 2.1 A y AA en las cuatro vistas, con el lector abierto, y el
// recorrido completo solo con teclado.
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { expect, test } from './comun';

async function graves(page: Page): Promise<string[]> {
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  return violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
}

const VISTAS: [string, string, (page: Page) => Promise<void>][] = [
  ['Inicio', '/#/', (p) => expect(p.locator('.q-entrada').first()).toBeVisible()],
  ['Lanzar', '/#/lanzar', (p) => expect(p.getByRole('button', { name: 'Generar orden' })).toBeVisible()],
  ['Progreso', '/#/novelas/demo-24/progreso', (p) => expect(p.locator('.q-tension').first()).toBeVisible()],
  ['Lectura con el lector', '/#/novelas/demo-24/lectura/3', (p) => expect(p.locator('.q-lector__texto')).toBeVisible()],
];

for (const [nombre, ruta, lista] of VISTAS) {
  test(`${nombre}: 0 violaciones serious o critical de axe (RNF-12)`, async ({ page }) => {
    await page.goto(ruta);
    await lista(page);
    expect(await graves(page)).toEqual([]);
  });
}

/** Tab hasta que el foco cumple `condicion`; falla si no llega en `maximo` pulsaciones. */
async function tabularHasta(page: Page, condicion: string, maximo = 60): Promise<void> {
  for (let i = 0; i < maximo; i++) {
    await page.keyboard.press('Tab');
    if (await page.evaluate((c) => document.activeElement?.matches(c) ?? false, condicion)) return;
  }
  throw new Error(`el foco no llega a ${condicion} en ${maximo} pulsaciones de Tab`);
}

test('recorrido completo solo con teclado (RNF-13, CA-28)', async ({ page, context, browserName }) => {
  if (browserName === 'chromium') await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/#/');
  await expect(page.locator('.q-entrada').first()).toBeVisible();
  // Abrir una novela y ver su progreso.
  await tabularHasta(page, '.q-entrada a[href="#/novelas/demo-24/progreso"]');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/progreso$/);
  await expect(page.getByText('cerrados: 7 de 24')).toBeVisible();
  // Abrir y cerrar un capítulo.
  await tabularHasta(page, 'a[href="#/novelas/demo-24/lectura"]');
  await page.keyboard.press('Enter');
  await tabularHasta(page, '.q-volumen[aria-current="true"]');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('[aria-current="true"]')).toHaveAttribute('data-capitulo', '3');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-capitulo="3"]')).toBeFocused();
  // Copiar una orden.
  await tabularHasta(page, 'a[href="#/lanzar"]', 80);
  await page.keyboard.press('Enter');
  await tabularHasta(page, '#lanzar-slug');
  await page.keyboard.type('nueva-prueba');
  await page.keyboard.press('Tab');
  await page.keyboard.type('Un faro apagado.');
  await tabularHasta(page, 'button.q-boton--primario');
  await page.keyboard.press('Enter');
  await expect(page.locator('.q-orden__texto').first()).toContainText('/novela-nueva nueva-prueba');
  await tabularHasta(page, '.q-orden button:not([disabled])');
  await page.keyboard.press('Enter');
  await expect(page.locator('.q-orden__estado').first()).not.toBeEmpty();
});
