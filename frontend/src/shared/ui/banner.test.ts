// RF-53, estructura del banner: titular, subtítulo y chips, todos en la mitad izquierda, y la
// decoración aparte y oculta a los lectores. Los datos de la novela los pone Progreso (T-10).
import { describe, expect, it } from 'vitest';
import { banner } from './banner';

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
