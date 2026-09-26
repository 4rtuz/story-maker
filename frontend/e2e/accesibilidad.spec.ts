// RNF-12 y RNF-13 (D12): axe con WCAG 2.1 A y AA en las cuatro vistas, con el lector abierto, y el
// recorrido completo solo con teclado.
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { expect, lanzamientoSimulado, test } from './comun';

async function graves(page: Page): Promise<string[]> {
  const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  return violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
}

const VISTAS: [string, string, (page: Page) => Promise<void>][] = [
  ['Inicio', '/#/', (p) => expect(p.locator('.q-obra[data-slug]').first()).toBeVisible()],
  ['Lanzar', '/#/lanzar', (p) => expect(p.getByRole('button', { name: 'Sí, es un regalo' })).toBeVisible()],
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

/** Tab (o `tecla`) hasta que el foco cumple `condicion`; falla si no llega en `maximo` pulsaciones. */
async function tabularHasta(page: Page, condicion: string, maximo = 60, tecla = 'Tab'): Promise<void> {
  for (let i = 0; i < maximo; i++) {
    await page.keyboard.press(tecla);
    if (await page.evaluate((c) => document.activeElement?.matches(c) ?? false, condicion)) return;
  }
  throw new Error(`el foco no llega a ${condicion} en ${maximo} pulsaciones de ${tecla}`);
}

test('recorrido completo solo con teclado (RNF-13, CA-28)', async ({ page }) => {
  await lanzamientoSimulado(page);
  await page.goto('/#/');
  await expect(page.locator('.q-obra[data-slug]').first()).toBeVisible();
  // Abrir una novela y ver su progreso.
  await tabularHasta(page, '.q-obra[data-slug="demo-24"] a[href="#/novelas/demo-24/progreso"]');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/progreso$/);
  await expect(page.getByText('de 24 capítulos')).toBeVisible();
  // Abrir y cerrar un capítulo desde el índice.
  await tabularHasta(page, 'a[href="#/novelas/demo-24/lectura"]');
  await page.keyboard.press('Enter');
  const tres = '[data-testid="indice-capitulo"][data-destino="3"]';
  await expect(page.locator(tres)).toBeVisible();
  await tabularHasta(page, tres);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog').locator('.q-lector__texto')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator(tres)).toBeFocused();
  // Lanzar una novela: hacia atrás, la barra lateral queda más cerca que el final de la ficha.
  await tabularHasta(page, 'a[href="#/lanzar"]', 30, 'Shift+Tab');
  await page.keyboard.press('Enter');
  await expect(page.locator('.q-chat__opciones .q-chip-opcion')).toHaveCount(2); // tras la pausa del asistente
  await tabularHasta(page, '.q-chat__opciones .q-chip-opcion:nth-child(2)'); // «No, es para mí»
  await page.keyboard.press('Enter');
  const respuesta = page.getByRole('textbox', { name: 'Tu respuesta' });
  await expect(respuesta).toBeFocused();
  await page.keyboard.type('Un faro apagado.');
  await page.keyboard.press('Enter');
  // Género y tono: Mayús + Tab desde la respuesta llega a «Omitir», la última opción.
  for (const pregunta of ['¿Qué tipo de suspense te apetece?', '¿Y el tono?']) {
    await expect(page.locator('.q-burbuja--bot').last()).toHaveText(pregunta);
    await expect(respuesta).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await page.keyboard.press('Enter');
  }
  for (const [pregunta, valor] of [
    ['¿Cuántos capítulos quieres que tenga?', '3'],
    ['¿Cuántas palabras en total, más o menos?', '9000'],
    ['Por último, dale un nombre corto para encontrarla: minúsculas, números y guiones.', 'nueva-prueba'],
  ] as const) {
    await expect(page.locator('.q-burbuja--bot').last()).toHaveText(pregunta);
    await expect(respuesta).toBeFocused();
    await page.keyboard.type(valor);
    await page.keyboard.press('Enter');
  }
  await expect(page.getByRole('button', { name: 'Lanzar novela' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('.q-burbuja--bot').last()).toContainText('¡En marcha!');
});
