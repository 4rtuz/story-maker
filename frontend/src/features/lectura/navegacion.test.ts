// CA-28 en su parte unitaria (D47): ← y → sin dar la vuelta, Enter abre y Esc cierra y devuelve
// el foco a la lista. La función pura y, después, la lista de la vista con el teclado.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { arrancar } from '../../app/rutas';
import { tecla } from './navegacion';
import { lectura } from './vista';
import { servirLectura } from './servir-lectura.test-util';

describe('tecla (D47)', () => {
  it('← y → mueven sin dar la vuelta', () => {
    expect(tecla('ArrowRight', 3, 24)).toEqual({ seleccion: 4 });
    expect(tecla('ArrowLeft', 3, 24)).toEqual({ seleccion: 2 });
    expect(tecla('ArrowLeft', 1, 24)).toEqual({ seleccion: 1 });
    expect(tecla('ArrowRight', 24, 24)).toEqual({ seleccion: 24 });
  });

  it('Enter abre, Esc cierra y el resto no hace nada', () => {
    expect(tecla('Enter', 5, 24)).toEqual({ seleccion: 5, accion: 'abrir' });
    expect(tecla('Escape', 5, 24)).toEqual({ seleccion: 5, accion: 'cerrar' });
    expect(tecla('a', 5, 24)).toBeNull();
  });
});

describe('teclado en la lista (CA-28)', () => {
  let parar: () => void;
  let raiz: HTMLElement;

  beforeEach(() => {
    vi.useFakeTimers();
    raiz = document.createElement('div');
    document.body.replaceChildren(raiz);
  });

  afterEach(() => {
    parar?.();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const pulsar = (key: string) =>
    document.activeElement?.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));
  const actual = () => raiz.querySelector('.q-volumenes [aria-current="true"]')?.getAttribute('data-capitulo');

  it('del 3, → pasa al 4, Enter abre el 4 y Esc cierra con el foco en el 4', async () => {
    servirLectura();
    location.hash = '#/novelas/demo-24/lectura';
    parar = arrancar(raiz, (ruta, navegar) => lectura(ruta as { vista: 'lectura'; slug: string }, navegar)).detener;
    await vi.advanceTimersByTimeAsync(0);
    raiz.querySelector<HTMLElement>('[data-capitulo="3"]')?.focus();
    pulsar('ArrowRight');
    expect(actual()).toBe('4');
    expect(document.activeElement?.getAttribute('data-capitulo')).toBe('4');
    pulsar('Enter');
    await vi.advanceTimersByTimeAsync(0);
    expect(location.hash).toBe('#/novelas/demo-24/lectura/4');
    expect(raiz.querySelector('[role="dialog"]')?.textContent).toContain('Capítulo cuatro');
    pulsar('Escape');
    await vi.advanceTimersByTimeAsync(0);
    expect(raiz.querySelector('[role="dialog"]')).toBeNull();
    expect(location.hash).toBe('#/novelas/demo-24/lectura');
    expect(document.activeElement?.getAttribute('data-capitulo')).toBe('4');
  });

  it('← en el 1 lo deja en el 1 y → en el 24 lo deja en el 24', async () => {
    servirLectura();
    location.hash = '#/novelas/demo-24/lectura';
    parar = arrancar(raiz, (ruta, navegar) => lectura(ruta as { vista: 'lectura'; slug: string }, navegar)).detener;
    await vi.advanceTimersByTimeAsync(0);
    raiz.querySelector<HTMLElement>('[data-capitulo="1"]')?.focus();
    pulsar('ArrowLeft');
    expect(actual()).toBe('1');
    raiz.querySelector<HTMLElement>('[data-capitulo="24"]')?.click();
    await vi.advanceTimersByTimeAsync(0);
    pulsar('Escape');
    await vi.advanceTimersByTimeAsync(0);
    pulsar('ArrowRight');
    expect(actual()).toBe('24');
  });
});
