// El estado de cada volumen (RF-24, D8): cerrado hasta el checkpoint, en curso si está en el índice
// y es posterior, pendiente en otro caso. Sin checkpoint no hay nada cerrado ni legible (VAL-15).

export type EstadoDeVolumen = 'cerrado' | 'en_curso' | 'pendiente';

/** Un estado por capítulo, del 1 a `total`. */
export function estadosDeVolumen(
  total: number,
  checkpoint: { capitulo: number } | null,
  indice: number[],
): EstadoDeVolumen[] {
  const cerrados = checkpoint?.capitulo ?? 0;
  const enIndice = new Set(indice);
  return Array.from({ length: total }, (_, i) => {
    const n = i + 1;
    if (n <= cerrados) return 'cerrado';
    return enIndice.has(n) ? 'en_curso' : 'pendiente';
  });
}
