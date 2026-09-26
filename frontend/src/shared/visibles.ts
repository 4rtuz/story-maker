// Las novelas que el panel no enseña en sus listas (spec 0015, RF-08; D5): evaluaciones, humo y la
// de regalo de pruebas. Siguen abriéndose por su ruta.
export const esVisible = (slug: string): boolean => !/^(eval|humo)-/.test(slug) && slug !== 'regalo-carmen';
