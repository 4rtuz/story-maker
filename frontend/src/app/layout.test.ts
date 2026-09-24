// CA-48 a CA-50 y CA-59 en su parte unitaria: estructura, atributos y nombres accesibles. Las
// medidas (270 y 72 px, el contorno de foco) no las calcula jsdom: las mide marca.spec.ts (VER-13).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorDeApi } from '../shared/api/errores';
import { crearLayout, type Layout } from './layout';

let layout: Layout;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-09-24T10:00:00'));
  layout = crearLayout();
  document.body.replaceChildren(layout.raiz);
});

afterEach(() => {
  vi.useRealTimers();
});

const nav = () => layout.raiz.querySelector('nav') as HTMLElement;
const items = () => [...nav().querySelectorAll('a')];
const ronda = (correcta: boolean, errores: ErrorDeApi[] = []) => ({
  cada: 10_000,
  correcta,
  errores,
  hora: new Date(),
});

describe('barra lateral (CA-48)', () => {
  it('en Progreso: logo, Navegación con Novelas y Lanzar, y el bloque de la novela', () => {
    layout.poner({ vista: 'progreso', slug: 'demo-24' }, 'Progreso', document.createElement('div'));
    const logo = nav().querySelector('img');
    expect(logo?.alt).toBe('Qaracter');
    expect(logo?.closest('.q-logo__marco')).not.toBeNull();
    expect(items().map((a) => [a.textContent, a.getAttribute('href')])).toEqual([
      ['Novelas', '#/'],
      ['Lanzar', '#/lanzar'],
      ['Progreso', '#/novelas/demo-24/progreso'],
      ['Lectura', '#/novelas/demo-24/lectura'],
    ]);
    expect(nav().textContent).toContain('demo-24');
    const actuales = items().filter((a) => a.getAttribute('aria-current') === 'page');
    expect(actuales.map((a) => a.textContent)).toEqual(['Progreso']);
  });

  it('en Inicio no hay bloque de novela', () => {
    layout.poner({ vista: 'inicio' }, 'Novelas', document.createElement('div'));
    expect(items().map((a) => a.textContent)).toEqual(['Novelas', 'Lanzar']);
    expect(items().find((a) => a.getAttribute('aria-current') === 'page')?.textContent).toBe('Novelas');
  });

  it('el estado de la API sale de las rondas, sin peticiones propias (D50)', () => {
    const espia = vi.fn();
    vi.stubGlobal('fetch', espia);
    layout.poner({ vista: 'inicio' }, 'Novelas', document.createElement('div'));
    const api = () => layout.raiz.querySelector('.q-api')?.textContent ?? '';
    expect(api()).toContain('sin datos');
    layout.informar(ronda(true));
    expect(api()).toContain('API conectada');
    expect(api()).toContain('http://127.0.0.1:8000');
    layout.informar(ronda(false, [new ErrorDeApi('red', 'API no disponible en http://127.0.0.1:8000')]));
    expect(api()).toContain('API sin respuesta');
    layout.informar(ronda(true));
    expect(api()).toContain('API conectada');
    layout.poner({ vista: 'invalida' }, 'Ruta no válida', document.createElement('div'));
    expect(api()).toContain('sin datos');
    expect(espia).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

describe('barra superior (CA-49)', () => {
  it('plegar, título y la hora de la última ronda correcta, que no cambia al fallar', async () => {
    layout.poner({ vista: 'progreso', slug: 'demo-24' }, 'Progreso', document.createElement('div'));
    const barra = layout.raiz.querySelector('header') as HTMLElement;
    expect(barra.querySelector('button')?.textContent).toBe('Plegar barra lateral');
    expect(barra.querySelector('h1')?.textContent).toBe('Progreso');
    layout.informar(ronda(true));
    expect(barra.textContent).toContain('Actualizado a las 10:00:00');
    await vi.advanceTimersByTimeAsync(10_000);
    layout.informar(ronda(false, [new ErrorDeApi('http', 'no existe la novela demo-24', 404)]));
    expect(barra.textContent).toContain('Actualizado a las 10:00:00');
  });

  it('el aviso de una ronda fallida conserva el contenido y se va en la siguiente correcta (CA-04)', () => {
    const contenido = document.createElement('p');
    contenido.textContent = 'cursor anterior';
    layout.poner({ vista: 'progreso', slug: 'demo-24' }, 'Progreso', contenido);
    layout.informar(ronda(false, [new ErrorDeApi('http', 'no existe la novela demo-24', 404)]));
    expect(layout.raiz.querySelector('[role="alert"]')?.textContent).toBe('no existe la novela demo-24');
    expect(layout.raiz.textContent).toContain('cursor anterior');
    layout.informar(ronda(true));
    expect(layout.raiz.querySelector('[role="alert"]')).toBeNull();
  });
});

describe('plegado (CA-50)', () => {
  it('pliega con nombres accesibles, cambia el botón y no guarda nada', () => {
    layout.poner({ vista: 'progreso', slug: 'demo-24' }, 'Progreso', document.createElement('div'));
    const boton = layout.raiz.querySelector('header button') as HTMLButtonElement;
    expect(boton.getAttribute('aria-expanded')).toBe('true');
    expect(document.getElementById(boton.getAttribute('aria-controls') ?? '')).toBe(nav());
    boton.click();
    expect(layout.raiz.classList).toContain('q-app--plegada');
    expect(boton.textContent).toBe('Desplegar barra lateral');
    expect(boton.getAttribute('aria-expanded')).toBe('false');
    expect(items().map((a) => a.textContent)).toEqual(['Novelas', 'Lanzar', 'Progreso', 'Lectura']);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).toBe('');
  });
});

describe('lo que no se muestra (CA-59)', () => {
  it('ni avatar, ni notificaciones, ni bienvenida, ni modo oscuro, ni idioma', () => {
    layout.poner({ vista: 'inicio' }, 'Novelas', document.createElement('div'));
    expect(layout.raiz.querySelector('[role="switch"], select')).toBeNull();
    expect(layout.raiz.textContent).not.toMatch(/avatar|notificaci|bienvenid|modo oscuro|idioma/i);
  });
});
