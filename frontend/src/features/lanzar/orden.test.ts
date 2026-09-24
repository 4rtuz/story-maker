// CA-11 y CA-15: la orden exacta y, bajo ella, las de la sesión del harness de AGENTS.md.
import { describe, expect, it } from 'vitest';
import { ordenesDeSesion, ordenNovelaNueva } from './orden';

describe('orden de /novela-nueva (CA-11)', () => {
  it('con capítulos y palabras', () => {
    expect(
      ordenNovelaNueva({ slug: 'nueva-prueba', idea: 'Un faro apagado.', capitulos: '3', palabras: '9000' }),
    ).toBe("/novela-nueva nueva-prueba --idea 'Un faro apagado.' --capitulos 3 --palabras 9000");
  });

  it('sin los opcionales, sin sus flags', () => {
    expect(ordenNovelaNueva({ slug: 'nueva-prueba', idea: 'Un faro apagado.', capitulos: '', palabras: '' })).toBe(
      "/novela-nueva nueva-prueba --idea 'Un faro apagado.'",
    );
  });

  it('solo palabras (VAL-9)', () => {
    expect(ordenNovelaNueva({ slug: 'nueva-prueba', idea: 'Un faro apagado.', capitulos: '', palabras: '80000' })).toBe(
      "/novela-nueva nueva-prueba --idea 'Un faro apagado.' --palabras 80000",
    );
  });
});

describe('órdenes de la sesión (CA-15)', () => {
  it('son las de AGENTS.md, literales, y la de continuar con el slug', () => {
    expect(ordenesDeSesion('nueva-prueba')).toEqual([
      'export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")',
      'claude --session-id "$NOVELA_SESSION_ID" --setting-sources project,local --model opus',
      '/novela-continuar nueva-prueba',
    ]);
  });
});
