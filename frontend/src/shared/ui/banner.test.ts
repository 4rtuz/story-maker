// RF-53, estructura del banner: titular, subtítulo y chips, todos en la mitad izquierda, y la
// decoración aparte y oculta a los lectores. Los datos de la novela los pone Progreso (T-10).
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../api/cliente';
import { banner, CURSOR_DE_MUESTRA, datosDeBanner } from './banner';

describe('banner de la novela (CA-53, parte unitaria)', () => {
  it('slug de titular, subgénero y «24 CAPÍTULOS» en mayúsculas, y un chip por campo del cursor', () => {
    const config = { parametros_obra: { subgenero: 'thriller_psicologico', num_capitulos: 24 } } as Esquemas['Config'];
    const cursor = { capitulo: 8, fase: 'escritura', ultimo_paso: 'briefing', intento: 1 } as const;
    const b = banner(datosDeBanner('demo-24', config, cursor));
    expect(b.querySelector('.q-banner__titular')?.textContent).toBe('demo-24');
    expect(b.querySelector('.q-banner__subtitulo')?.textContent).toBe('THRILLER PSICOLÓGICO · 24 CAPÍTULOS');
    expect([...b.querySelectorAll('.q-chip')].map((c) => c.textContent)).toEqual([
      'Fase: escritura',
      'Capítulo: 8',
      'Último paso: briefing',
      'Intento: 1',
    ]);
  });

  it('sin config ni cursor todavía, solo el titular', () => {
    const b = banner(datosDeBanner('demo-24', undefined, undefined));
    expect(b.querySelector('.q-banner__titular')?.textContent).toBe('demo-24');
    expect(b.querySelectorAll('.q-chip')).toHaveLength(0);
  });
});

const ejemplo = () =>
  banner({
    titular: 'una-novela-de-prueba',
    subtitulo: 'THRILLER PSICOLÓGICO · 3 CAPÍTULOS',
    chips: [
      { etiqueta: 'Fase', valor: 'escritura', icono: 'activity' },
      { etiqueta: 'Capítulo', valor: '2', icono: 'book-open' },
    ],
  });

describe('banner', () => {
  it('pone titular, subtítulo y chips dentro del bloque de texto', () => {
    const b = ejemplo();
    const texto = b.querySelector('.q-banner__texto');
    expect(texto?.querySelector('.q-banner__titular')?.textContent).toBe('una-novela-de-prueba');
    expect(texto?.querySelector('.q-banner__subtitulo')?.textContent).toBe(
      'THRILLER PSICOLÓGICO · 3 CAPÍTULOS',
    );
    const chips = [...(texto?.querySelectorAll('.q-chip') ?? [])].map((c) => c.textContent);
    expect(chips).toEqual(['Fase: escritura', 'Capítulo: 2']);
  });

  it('la decoración queda fuera del texto y oculta a los lectores de pantalla', () => {
    const decoracion = ejemplo().querySelector('.q-banner__teselas');
    expect(decoracion?.getAttribute('aria-hidden')).toBe('true');
    expect(decoracion?.closest('.q-banner__texto')).toBeNull();
  });

});

describe('banner con los chips aún por llegar (RNF-21)', () => {
  it('reserva su sitio con chips invisibles y ocultos a los lectores', () => {
    const reservarChips = datosDeBanner('demo-24', undefined, CURSOR_DE_MUESTRA).chips;
    const b = banner({ titular: 'demo-24', subtitulo: '', chips: [], reservarChips });
    const reserva = b.querySelector('.q-banner__chips');
    expect(reserva?.classList.contains('q-banner__chips--reserva')).toBe(true);
    expect(reserva?.getAttribute('aria-hidden')).toBe('true');
    expect(reserva?.querySelectorAll('.q-chip')).toHaveLength(4);
    expect(b.querySelector<HTMLElement>('.q-banner__subtitulo')?.hidden).toBe(false);
  });
});
