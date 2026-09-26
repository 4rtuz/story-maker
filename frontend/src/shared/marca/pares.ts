// Los pares de roles en uso, con su tipo (spec 0004 §8.4, D22). pares.test.ts recalcula cada
// contraste desde tokens.css; un par que se use y no esté aquí no se comprueba (VAL-27), así que
// una combinación nueva de primer plano y fondo en un componente entra también en esta lista.

export type TipoDePar = 'texto' | 'texto-grande' | 'no-textual';

export interface Par {
  readonly primerPlano: string;
  readonly fondo: string;
  /** El fondo opaco sobre el que se compone `fondo` cuando tiene transparencia. */
  readonly sobre?: string;
  readonly tipo: TipoDePar;
}

export const UMBRALES: Readonly<Record<TipoDePar, number>> = {
  texto: 4.5,
  'texto-grande': 3,
  'no-textual': 3,
};

export const PARES: readonly Par[] = [
  { primerPlano: '--q-texto', fondo: '--q-fondo-tarjeta', tipo: 'texto' },
  { primerPlano: '--q-texto', fondo: '--q-fondo-pagina', tipo: 'texto' },
  { primerPlano: '--q-texto', fondo: '--q-secundario-fondo', tipo: 'texto' },
  { primerPlano: '--q-texto', fondo: '--q-tinte-naranja', tipo: 'texto' },
  { primerPlano: '--q-texto-secundario', fondo: '--q-fondo-tarjeta', tipo: 'texto' },
  { primerPlano: '--q-texto-sobre-primario', fondo: '--q-primario', tipo: 'texto' },
  { primerPlano: '--q-texto-sobre-primario', fondo: '--q-nav-activo-fondo', tipo: 'texto' },
  { primerPlano: '--q-nav-texto', fondo: '--q-nav-fondo', tipo: 'texto' },
  // El hover de los ítems de navegación (T-07).
  { primerPlano: '--q-nav-texto', fondo: '--q-nav-separador', tipo: 'texto' },
  // Rótulos de bloque y URL de la API en la barra lateral.
  { primerPlano: '--q-nav-texto-secundario', fondo: '--q-nav-fondo', tipo: 'texto' },
  { primerPlano: '--q-banner-texto', fondo: '--q-deco-banner-inicio', tipo: 'texto' },
  { primerPlano: '--q-banner-subtitulo', fondo: '--q-deco-banner-inicio', tipo: 'texto' },
  {
    primerPlano: '--q-banner-texto',
    fondo: '--q-chip-fondo',
    sobre: '--q-deco-banner-inicio',
    tipo: 'texto',
  },
  { primerPlano: '--q-icono-naranja', fondo: '--q-tinte-naranja', tipo: 'no-textual' },
  { primerPlano: '--q-icono-cian', fondo: '--q-tinte-cian', tipo: 'no-textual' },
  { primerPlano: '--q-nav-indicador', fondo: '--q-nav-fondo', tipo: 'no-textual' },
  { primerPlano: '--q-borde-campo', fondo: '--q-fondo-tarjeta', tipo: 'no-textual' },
  { primerPlano: '--q-foco', fondo: '--q-fondo-tarjeta', tipo: 'no-textual' },
  { primerPlano: '--q-foco', fondo: '--q-fondo-pagina', tipo: 'no-textual' },
  { primerPlano: '--q-foco-sobre-oscuro', fondo: '--q-nav-fondo', tipo: 'no-textual' },
  { primerPlano: '--q-foco-sobre-oscuro', fondo: '--q-deco-banner-inicio', tipo: 'no-textual' },
  { primerPlano: '--q-primario', fondo: '--q-fondo-tarjeta', tipo: 'no-textual' },
  { primerPlano: '--q-icono-cian', fondo: '--q-fondo-tarjeta', tipo: 'no-textual' },
  // Spec 0015: etiquetas de estado, título sobre la portada, marca y carga del proceso de creación.
  { primerPlano: '--q-estado-hecho', fondo: '--q-estado-hecho-fondo', tipo: 'texto' },
  { primerPlano: '--q-estado-vivo', fondo: '--q-estado-vivo-fondo', tipo: 'texto' },
  { primerPlano: '--q-estado-pausa', fondo: '--q-estado-pausa-fondo', tipo: 'texto' },
  { primerPlano: '--q-estado-bloqueo', fondo: '--q-estado-bloqueo-fondo', tipo: 'texto' },
  { primerPlano: '--q-portada-texto', fondo: '--q-portada-velo', sobre: '--q-fondo-tarjeta', tipo: 'texto' },
  { primerPlano: '--q-estado-hecho', fondo: '--q-fondo-tarjeta', tipo: 'no-textual' },
  { primerPlano: '--q-estado-vivo', fondo: '--q-fondo-tarjeta', tipo: 'no-textual' },
  // El libro abierto: texto y capitular de cada fondo.
  { primerPlano: '--q-lector-tinta', fondo: '--q-lector-papel', tipo: 'texto' },
  { primerPlano: '--q-lector-tinta', fondo: '--q-lector-sepia', tipo: 'texto' },
  { primerPlano: '--q-lector-tinta-noche', fondo: '--q-lector-noche', tipo: 'texto' },
  { primerPlano: '--q-lector-acento', fondo: '--q-lector-papel', tipo: 'texto' },
  { primerPlano: '--q-lector-acento', fondo: '--q-lector-sepia', tipo: 'texto-grande' },
  { primerPlano: '--q-lector-acento-noche', fondo: '--q-lector-noche', tipo: 'texto' },
  { primerPlano: '--q-foco', fondo: '--q-lector-sepia', tipo: 'no-textual' },
  { primerPlano: '--q-lector-acento-noche', fondo: '--q-lector-noche', tipo: 'no-textual' },
];
