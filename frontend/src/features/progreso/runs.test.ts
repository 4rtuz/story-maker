// CA-21: los manifiestos en orden de run_id, con sus seis campos, y «árbol sucio» solo donde toca.
import { describe, expect, it } from 'vitest';
import type { Esquemas } from '../../shared/api/cliente';
import { listaDeRuns } from './runs';

const manifiesto = (run_id: string, capitulo: number, sucio: boolean): Esquemas['Manifest'] => ({
  schema_version: '1.0.0',
  run_id,
  capitulo,
  fase: 'capitulo',
  creado: '2026-09-24T10:00:00+02:00',
  sha_commit: '0123456789abcdef0123456789abcdef01234567',
  version_recetas: 'a'.repeat(64),
  version_canon: 'b'.repeat(64),
  version_plan: 'c'.repeat(64),
  sucio,
  hashes_claude: {},
});

describe('runs (CA-21)', () => {
  it('dos entradas en orden, con los seis campos, y solo la segunda con «árbol sucio»', () => {
    const lista = listaDeRuns([manifiesto('r-20260924-0001', 1, false), manifiesto('r-20260924-0002', 2, true)]);
    const runs = [...lista.querySelectorAll('li')];
    expect(runs.map((r) => r.querySelector('.q-run__id')?.textContent)).toEqual(['r-20260924-0001', 'r-20260924-0002']);
    const [primero, segundo] = runs;
    expect(primero?.textContent).toContain('capitulo'); // la fase
    expect(primero?.textContent).toContain('capítulo 1');
    expect(primero?.querySelector('.q-sha')?.textContent).toBe('0123456');
    expect(primero?.querySelector('.q-sha')?.getAttribute('title')).toBe('0123456789abcdef0123456789abcdef01234567');
    expect(primero?.querySelector('time')?.getAttribute('datetime')).toBe('2026-09-24T10:00:00+02:00');
    expect(primero?.textContent).not.toContain('árbol sucio');
    expect(segundo?.textContent).toContain('árbol sucio');
  });
});
