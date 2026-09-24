// Las órdenes que prepara Lanzar (RF-11, RF-14, RF-15; D5, D44). El panel no las ejecuta: las
// muestra para copiarlas en la sesión del harness.
import type { Campos } from './validacion';

/** Entre comillas simples y con cada `'` como `'\''`: dentro de ellas bash no interpreta `$`, `` ` ``,
 * `\`, `!` ni los saltos de línea, con o sin expansión del historial (D44, que sustituye a D7). */
export function entrecomillar(texto: string): string {
  return `'${texto.replaceAll("'", "'\\''")}'`;
}

export function ordenNovelaNueva({ slug, idea, capitulos, palabras }: Campos): string {
  const opcionales = [capitulos && `--capitulos ${capitulos}`, palabras && `--palabras ${palabras}`];
  return [`/novela-nueva ${slug} --idea ${entrecomillar(idea)}`, ...opcionales].filter(Boolean).join(' ');
}

/** Las dos órdenes que abren la sesión interactiva del harness, tal como están en AGENTS.md
 * § Proceso: ejecución, y la de continuación. */
export function ordenesDeSesion(slug: string): string[] {
  return [
    'export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")',
    'claude --session-id "$NOVELA_SESSION_ID" --setting-sources project,local --model opus',
    `/novela-continuar ${slug}`,
  ];
}
