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
];
