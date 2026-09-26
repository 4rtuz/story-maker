// La conversación de Lanzar (spec 0015, RF-09): el orden de las preguntas, qué se puede omitir,
// la validación de cada respuesta y la petición que sale al final.
import { describe, expect, it } from 'vitest';
import { inicial, pregunta, responder, resumen, sugerirSlug, type Conversacion } from './conversacion';
import { peticion } from './validacion';

/** Responde en orden y falla si alguna respuesta no se acepta. */
function charlar(respuestas: string[], existentes: string[] = []): Conversacion {
  return respuestas.reduce((c, r) => {
    const { conversacion, error } = responder(c, r, existentes);
    if (error) throw new Error(`«${r}» en ${c.paso}: ${error}`);
    return conversacion;
  }, inicial());
}

describe('conversación de Lanzar', () => {
  it('sin regalo: idea, género, tono, capítulos, palabras y nombre corto; nunca la extensión', () => {
    const pasos: string[] = [];
    let c = inicial();
    for (const r of ['no', 'Un faro apagado.', 'noir', '', '12', '60000', 'faro-apagado']) {
      pasos.push(c.paso);
      c = responder(c, r, []).conversacion;
    }
    expect(pasos).toEqual(['regalo', 'idea', 'genero', 'tono', 'capitulos', 'palabras', 'slug']);
    expect(c.paso).toBe('resumen');
    expect(pregunta(c)).toBeNull();
    expect(peticion(c.campos)).toEqual({ slug: 'faro-apagado', idea: 'Género: noir.\n\nUn faro apagado.', capitulos: 12, palabras: 60000 });
  });

  it('con regalo pregunta por la persona, y entonces la idea se puede omitir', () => {
    const c = charlar(['si', 'Ana', '40', 'curiosa', '', '']);
    expect(c.paso).toBe('genero');
    expect(c.campos).toMatchObject({ nombre: 'Ana', edad: '40', rasgos: 'curiosa', recuerdos: '', idea: '' });
  });

  it('capítulos y palabras no se pueden omitir', () => {
    const c = charlar(['no', 'Un faro apagado.', '', '']);
    expect(pregunta(c)?.omitible).toBe(false);
    expect(responder(c, '', []).error).toBeTruthy();
  });

  it('una respuesta inválida da su motivo y repite la pregunta', () => {
    const c = charlar(['no', 'Un faro apagado.', '', '']);
    const { conversacion, error } = responder(c, 'muchos', []);
    expect(error).toContain('entero');
    expect(conversacion).toBe(c);
  });

  it('sin regalo, la idea es obligatoria', () => {
    const c = charlar(['no']);
    expect(pregunta(c)?.omitible).toBe(false);
    expect(responder(c, '   ', []).error).toBeTruthy();
  });

  it('las palabras admiten separador de miles', () => {
    const c = charlar(['no', 'Un faro apagado.', '', '', '10', '80.000']);
    expect(c.campos.palabras).toBe('80000');
  });

  it('un nombre corto que ya existe no se acepta', () => {
    const c = charlar(['no', 'Un faro apagado.', '', '', '10', '30000']);
    expect(responder(c, 'demo', ['demo']).error).toContain('ya existe');
  });

  it('las opciones de género y tono salen de validacion.ts', () => {
    const c = charlar(['no', 'Un faro apagado.']);
    expect(pregunta(c)?.opciones.map((o) => o.valor)).toContain('noir');
  });

  it('el resumen lista lo contestado', () => {
    const c = charlar(['no', 'Un faro apagado.', 'noir', 'oscuro', '10', '30000', 'faro']);
    expect(resumen(c)).toEqual([
      ['Idea', 'Un faro apagado.'],
      ['Género', 'Noir'],
      ['Tono', 'Oscuro'],
      ['Capítulos', '10'],
      ['Palabras', '30.000'],
      ['Nombre corto', 'faro'],
    ]);
  });
});

describe('sugerirSlug', () => {
  it('las primeras palabras con contenido de la idea, sin tildes ni signos', () => {
    expect(sugerirSlug('¡Un faro apagado en la costa de Cádiz!', [])).toBe('faro-apagado-costa-cadiz');
  });

  it('si ya existe, con sufijo', () => {
    expect(sugerirSlug('Faro', ['faro'])).toBe('faro-2');
  });

  it('sin idea, un nombre genérico', () => {
    expect(sugerirSlug('', [])).toBe('novela-nueva');
  });
});
