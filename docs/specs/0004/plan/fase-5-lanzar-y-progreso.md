# Fase 5: Lanzar y Progreso

Plan: `README.md` · Spec: §5 (RF-11 a RF-23, RF-53 a RF-55, RF-58), §8.4 (orden de Lanzar, gráfica, recursos por vista, mensajes, estructura) · Decisiones: D4 a D6, D8, D10, D12, D21, D22, D24, D36, D38, D41 a D46 (D7 queda sustituida por D44)

Independiente de la fase 6. Cada vista construye sus modelos con funciones puras —orden y entrecomillado de la idea, resumen, serie de tensión, registro del log— que se prueban sin DOM; la cáscara (`vista.ts`) se prueba con jsdom. Toda escritura en el DOM usa `textContent` y `createElement`.

---

#### T-09 Lanzar

- Descripción: `features/lanzar/validacion.ts` (slug; idea que no esté vacía ni hecha solo de `\s`, incluidos tabuladores y saltos de línea, D42; capítulos contra `^[1-9][0-9]{0,2}$` y palabras contra `^[1-9][0-9]*$`, sin normalizar, D41; slug existente en `GET /novelas`, o aviso «no se ha podido comprobar si el slug ya existe» si esa petición no ha respondido o ha fallado, sin bloquear la orden, D43), `features/lanzar/orden.ts` (orden `/novela-nueva <slug> --idea '<idea>'` con `--capitulos` y `--palabras` solo si se rellenan; debajo, las dos órdenes de apertura de la sesión del harness y `/novela-continuar <slug>`, copiadas literalmente de la spec §8.4), el entrecomillado de la idea entre comillas simples con cada `'` sustituida por `'\''`, conservando saltos de línea (D44, que sustituye a D7), y `features/lanzar/vista.ts` (formulario, «Generar orden», bloque en `--q-fuente-mono`, «Copiar» con `navigator.clipboard.writeText`, deshabilitado sin orden, y alternativa con campo de solo lectura seleccionado y «pulsa Ctrl+C para copiar»). La vista solo pide `GET /novelas` y no produce ficheros (RF-16).
- Orden TDD:
  1. Rojo, `frontend/src/features/lanzar/orden.test.ts`: la orden exacta de CA-11, con y sin campos opcionales; las tres órdenes de CA-15 bajo ella.
  2. Rojo, `frontend/src/features/lanzar/validacion.test.ts`: `Nueva_Prueba`, tres espacios, un tabulador y un salto de línea, capítulos `0`, `1000`, `2.5`, `07`, ` 3` y `+3`, y palabras `0`, `09000` y `-1` dan su motivo, no se normalizan y no dan orden; capítulos `1` y palabras `1`, y capítulos `999`, sí la dan (CA-12); `demo-24` existente da el texto de CA-13 y ninguna orden; y con `GET /novelas` fallido o pendiente, la orden sale con el aviso de D43 (CA-13).
  3. Rojo, `frontend/src/features/lanzar/escapado.test.ts` con fast-check, ≥ 200 casos con comillas simples y dobles, barras —también al final y ante un salto de línea—, `$`, `$(…)`, acentos graves, `!`, saltos de línea, tildes y eñes, más casos fijos (`'`, `fin\`, `$(id)`, `` `id` ``, `!!`, una idea que termina en salto de línea): se extrae el argumento `--idea '…'` y `bash -c 'printf %s …'` devuelve la idea exacta, una vez tal cual y otra con `set -H`, sin ejecutar ninguna orden (CA-14). Necesita `bash` en el `PATH`, también en Windows con Git Bash; sin bash, el test falla con un mensaje que lo nombra, no se salta (D36).
  4. Rojo, `frontend/src/features/lanzar/vista.test.ts`: «Copiar» escribe en el portapapeles simulado; con el portapapeles denegado, el texto queda seleccionado con el aviso; esqueleto, vacío y error de `GET /novelas` (CA-58, parte unitaria); ningún control ejecuta órdenes.
  5. Verde.
- Archivos: `frontend/src/features/lanzar/{vista,orden,validacion}.ts` (nuevos) · `frontend/src/features/lanzar/escapado.ts` (nuevo; la spec lo pone junto a `orden.ts`, se puede fundir con él) · `frontend/src/features/lanzar/{orden,validacion,escapado,vista}.test.ts` (nuevos) · `frontend/src/app/rutas.ts` (modificar) · `docs/architecture.md` §11.2 y §12.8 (modificar)
- Cubre: RF-11, RF-12, RF-13, RF-14, RF-15, RF-16 (parte unitaria), RF-45, RF-58
- Criterios: CA-11, CA-12, CA-13, CA-14, CA-15; CA-16 se cierra en T-16
- Documentación: `docs/architecture.md` §11.2 (`:858`), donde el formulario deja de producir un `config.yaml` y prepara la orden (D5), y §12.8 (`:875`), la frase «El formulario del panel produce un `config.yaml`…».
- Depende de: T-07
- Hecho cuando: los cuatro tests se han visto en rojo y pasan, CA-14 con al menos 200 casos y también en Windows con Git Bash; `npm run verificar` en verde.
- Complejidad: M

#### T-10 Progreso: banner, métricas, hilos y runs

- Descripción: `features/progreso/vista.ts` con el banner (slug en `--q-fuente-display`, subtítulo en mayúsculas con la etiqueta del `subgenero` desde una tabla exhaustiva sobre el tipo generado, que `tsc` comprueba, y «<N> CAPÍTULOS», más un chip por campo del cursor), la fila de cuatro tarjetas de métrica y la rejilla de tarjetas (dos columnas desde 1280 px, una por debajo, sin desplazamiento horizontal); `features/progreso/resumen.ts` (cursor tal cual, «cerrados: <n> de <total>» desde `checkpoint.capitulo` o 0, `palabras_totales` junto a `longitud_total_palabras`, `desviacion_vs_plan`, hilos con `estado: "abierto"`); `features/progreso/runs.ts` (tabla por `run_id` con los seis campos y «árbol sucio»; «sin runs todavía»). Recursos a 10 s: `estado`, `config`, `escaleta`, `checkpoint`, `capitulos` y `runs` (spec §8.4).
- Orden TDD:
  1. Rojo, `frontend/src/features/progreso/resumen.test.ts`: con 7 cerrados de 24, «cerrados: 7 de 24»; con `checkpoint` `null`, «cerrados: 0 de 24» (CA-17); solo `hil-001` de un estado con `hil-001` abierto y `hil-002` cerrado (CA-20); «no hay hilos abiertos».
  2. Rojo, `frontend/src/features/progreso/runs.test.ts`: dos manifiestos en orden, solo el segundo con «árbol sucio» (CA-21).
  3. Rojo, `frontend/src/shared/ui/banner.test.ts` (existe desde T-20): titular `demo-24`, subtítulo con el subgénero y «24 CAPÍTULOS», cuatro chips (CA-53, parte unitaria).
  4. Rojo, `frontend/src/features/progreso/vista.test.ts`: esqueleto, vacío y error; con un 404 en `estado` se conserva el cursor anterior (CA-04 y CA-58, parte unitaria).
  5. Verde.
- Archivos: `frontend/src/features/progreso/{vista,resumen,runs}.ts` (nuevos) · `frontend/src/features/progreso/{vista,resumen,runs}.test.ts` (nuevos) · `frontend/src/shared/ui/banner.test.ts` (modificar) · `frontend/src/app/rutas.ts` (modificar)
- Cubre: RF-17, RF-20, RF-21, RF-53, RF-54 (disposición; se mide en T-21), RF-58
- Criterios: CA-17, CA-20, CA-21; CA-53 en su parte unitaria; CA-54 se cierra en T-21
- Documentación: ninguna asignada.
- Depende de: T-07
- Hecho cuando: los cuatro tests se han visto en rojo y pasan; `npm run verificar` en verde.
- Complejidad: M

#### T-11 Progreso: tensión

- Descripción: `features/progreso/tension.ts` construye `SerieDeTension` como función pura: `objetivo` por capítulo, tramos de `real` separados en cada `null`, capítulos «sin puntuar», bandas por acto y cinco marcas de giro. Sobre ella, SVG creado con `createElementNS` —real continua en `--q-primario`, objetivo discontinua en `--q-icono-cian`, bandas en `--q-secundario-fondo` rotuladas «Acto N», giros en `--q-texto-secundario`— y una tabla equivalente. Colores leídos con el lector de tokens de T-19 (RF-55). Sin escaleta (404): solo la serie real y «el plan todavía no tiene escaleta», sin aviso de error. Con `tension_real` vacío o todo `null`: «todavía no hay tensión puntuada», con la curva objetivo dibujada. Con más entradas reales que objetivo, el eje x llega hasta el mayor de los dos tamaños (D46).
- Orden TDD:
  1. Rojo, `frontend/src/features/progreso/tension.test.ts`: el caso exacto de CA-18 (dos tramos 1–2 y 4–5, «sin puntuar» en el 3, sin valor en el 6, 2 bandas, 5 giros, 6 filas con «sin puntuar» y «—»); `[null, null]` con el estado de vacío y la curva objetivo; 8 entradas reales con una curva de 6 llegan al capítulo 8; un valor real aislado entre `null` deja un elemento SVG visible; sin escaleta, solo la serie real y el texto (CA-19, parte unitaria); con el lector de tokens alimentado con `tokens.css`, colores de sus roles, y un cambio de `--q-primario` en el test que llega a la serie real (CA-55, parte de la gráfica).
  2. Verde.
- Archivos: `frontend/src/features/progreso/tension.ts` (nuevo) · `frontend/src/features/progreso/tension.test.ts` (nuevo) · `frontend/src/features/progreso/vista.ts` (modificar) · `docs/architecture.md` §11.2 (modificar)
- Cubre: RF-18, RF-19, RF-45, RF-55
- Criterios: CA-18; CA-19 y CA-55 en su parte unitaria
- Documentación: `docs/architecture.md` §11.2 (`:862`): «Si necesita un dato que no está en el estado, se añade al estado» pasa a «se sirve desde la API con su modelo de dominio» (D4).
- Depende de: T-10
- Hecho cuando: el test se ha visto en rojo y pasa; `tokens.test.ts` sigue en verde (ningún color literal en la gráfica); `npm run verificar` en verde.
- Complejidad: M

#### T-12 Progreso: actividad

- Descripción: `features/progreso/actividad.ts` con el `Registro` (`run_id` que sigue, siguiente `desde`, 50 últimas líneas y `modificado`) como función pura de encadenado: primera petición con `desde=0`, cada siguiente con el `hasta` anterior, reinicio a `desde=0` y reconstrucción tras un 416, sin aviso; y, cuando `…/runs` trae un run de `run_id` mayor, cambio a él con `desde=0` y lista nueva. No hay selección de run ni entrada de run (D38). Sondeo a 3 s del run de `run_id` mayor, líneas en `--q-fuente-mono`, hora de `modificado`, «sin actividad registrada» si `modificado` es `null`, y «sin actividad desde <hora>» cuando pasan más de 15 min. Sin runs, ninguna petición de log.
- Orden TDD:
  1. Rojo, `frontend/src/features/progreso/actividad.test.ts` con reloj simulado: log de 120 líneas, 6 s de reloj, `desde` encadenado, 50 líneas visibles, la hora; un 416 vuelve a `desde=0`; siguiendo un run con `hasta` 4 000, la aparición de un run mayor hace que su primera petición lleve `desde=0` y que no se pida más el anterior (CA-22); 16 min muestran el aviso y 14 min no, comparando instantes con zona y sin rótulo si `modificado` está en el futuro (CA-23).
  2. Verde.
- Archivos: `frontend/src/features/progreso/actividad.ts` (nuevo) · `frontend/src/features/progreso/actividad.test.ts` (nuevo) · `frontend/src/features/progreso/vista.ts` (modificar)
- Cubre: RF-22, RF-23
- Criterios: CA-22, CA-23
- Documentación: ninguna asignada.
- Depende de: T-10
- Hecho cuando: el test se ha visto en rojo y pasa; el recuento de `sondeo.test.ts` sigue ≤ 60 peticiones por minuto con el log incluido (RNF-05); `npm run verificar` en verde.
- Complejidad: M
