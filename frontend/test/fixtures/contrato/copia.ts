// CA-02: lo que contrato.test.ts tiene que encontrar, un esquema del OpenAPI copiado a mano.
export interface Checkpoint {
  capitulo: number;
}

// Un nombre que no es de ningún esquema no cuenta.
export type Vista = 'inicio' | 'lanzar';
