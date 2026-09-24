// La x de cada volumen en la estantería (RF-24, spec §8.4): x = (n − 1) × 1,2 + a × 2,0, con `a`
// los actos anteriores al del capítulo. Un acto es anterior a n si todos sus capítulos lo son, así
// que un capítulo fuera de acto no suma hueco propio y la x sigue creciendo con n.

export const PASO = 1.2;
export const HUECO_DE_ACTO = 2.0;

export function disposicion(total: number, actos: { capitulos: number[] }[] | null): number[] {
  const finales = (actos ?? []).filter((a) => a.capitulos.length).map((a) => Math.max(...a.capitulos));
  return Array.from({ length: total }, (_, i) => {
    const n = i + 1;
    const anteriores = finales.filter((f) => f < n).length;
    return i * PASO + anteriores * HUECO_DE_ACTO;
  });
}
