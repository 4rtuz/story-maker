---
spec: 0002
titulo: "Verificación a escala de novela: secreto, estado, estilo, tensión y orquestador"
estado: aceptada
autor: "arturo.soto"
fecha: 2026-09-24
version: 0.3
afecta: [backend, agentes, esquemas, docs]
depende_de: [0001, 0003]
sustituye: []
adr: [0002]
commit: null
---

# 0002 — Verificación a escala de novela: secreto, estado, estilo, tensión y orquestador

## 1. Propósito y alcance

La spec cierra los cinco modos de fallo que `docs/validators.md` describe y que ningún gate actual detecta: el misterio roto, la contaminación del estado, la deriva de estilo, el colapso de la tensión y la degradación silenciosa de la sesión orquestadora. Sirve al orquestador, que hoy los descubriría tarde, y a quien lea la novela.

La spec 0001 v0.3 ya fija la **forma** que esto necesita: custodia por hash, sello de capítulos cerrados, `cita` opcional en las colecciones append-only y fichas de personaje estructuradas (0001 §5.6). Esta spec es la **política** que usa esos campos. La 0003 dejó construidos los agentes, el hook y la novela de humo `humo-0003`, que da los datos con que se cerraron las preguntas de la v0.2 (§16).

**Dentro del alcance**

- Secreto: filtrado por campo de la ficha de personaje, solape con lo no revelado, QA saneado en el briefing de reintento, sondas ciegas, y pistas y pistas falsas con cita.
- Estado: cita obligatoria, invariantes narrativos del delta, resúmenes acotados y cruce con el plan.
- Estilo: léxico vetado, huella estilométrica, origen del score `estilo` y modelo resuelto por agente.
- Tensión: `novela validar-plan`, carga de preguntas abiertas, banda y tendencia, gancho con cita, auditoría de acto y calibración del juez.
- Orquestador: `novela gate`, `novela sonda`, auditoría de trayectoria, freno en `pendiente`, contexto medido y canario del orquestador.
- Política de cuota: `architecture.md` §9 deja de describir niveles que reescriben un capítulo cerrado.

**Fuera del alcance**

- Lo que ya está en la 0001 v0.3 (RF-30 a RF-36).
- La contención de la 0003: agentes, hooks, permisos y canario de las barreras. Esta spec los amplía (un agente, una salida y un hook `Stop`), pero no los rediseña.
- `novela budget` y la degradación por cuota medida (P-16): van a una spec propia cuando haya datos de consumo por ventana.
- El índice recuperable (`architecture.md` §12.4).
- El solape de escenas en `linea_temporal` y el objeto de relevancia alta sin poseedor ni ubicación: se descartan con la evidencia de `humo-0003` (§15).
- Los prompts concretos de los agentes. Esta spec fija contratos de entrada y salida; el texto de los prompts se valida con una novela de humo (`AGENTS.md`).
- Los fallos en `propuesto` de `validators.md` §4.17 (F-27, F-37 y F-56 a F-59).

## 2. Problema

Cada capítulo puede pasar todos sus gates mientras la novela falla en conjunto. La novela de humo de la 0003 (`humo-0003`, 2026-09-24) lo confirma con casos reales:

- **El secreto viaja parafraseado.** El guardarraíl de RF-09 busca texto literal de `misterio.md`. Tres vías llegan al `escritor` sin pasar por él: las fichas del `trazador`, que conoce la solución; la ficha del culpable, cuyo `secreto` es la solución; y el `qa/` del reintento, escrito por revisores que la ven (`validators.md` §4.9). Es un riesgo que la 0003 aceptó a la espera de esta spec (0003 §13).
- **El `cronista` escribe en tablas que no admiten corrección.** La cita de `hec-002` es literal, pero no contiene la fecha que afirma el hecho, y el capítulo 3 chocó con ella (`validators.md` §5.9, condición cumplida). Además, el delta del capítulo 2 no trae ni una cita en `linea_temporal`, Los tres deltas dan estado a `per-anselmo`, que no tiene ficha en el canon ni en el plan, y sitúan a personajes y objetos en escenarios que no existen: `esc-torre-faro` donde el canon y el plan dicen `esc-faro-de-cabo-ermo`.
- **La deriva de estilo no se mide.** El `editor-estilo` se puntúa a sí mismo: el score `estilo` sale de su veredicto. Y la longitud media de frase de los tres capítulos (7,9–8,4 palabras) está a un 46 % de la que declara `ritmo` (15), sin que nada lo registre.
- **El gate de tensión no tiene banda**, y el `lector-suspense` puntúa la previsibilidad conociendo la solución (§4.2, §4.13).
- **El orden del bucle solo está escrito en prosa, y la cuenta de intentos la lleva la sesión.** En el capítulo 3, la sesión informó 1 de 2 reintentos de revisión, y la cuenta de `harness.log` daba 2 (F-31).

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Orquestador | Deja de decidir los gates y de contar intentos: lo hace `novela gate` (ADR 0002). Gana la auditoría de su trayectoria y un freno en `pendiente` |
| Agente `escritor` | Recibe fichas filtradas y un briefing de reintento propio con el QA saneado; su frontmatter lleva citas de pistas y pistas falsas |
| Agente `cronista` | La cita es obligatoria en las cuatro colecciones; sus deltas pasan por los invariantes narrativos y el control de resúmenes |
| Agentes `continuista`, `lector-suspense` | Su QA llega saneado al escritor. El `lector-suspense` devuelve `gancho` y deja de puntuar la previsibilidad |
| Agente `editor-estilo` | Su score lo calcula el CLI desde la huella; el léxico vetado se comprueba tras su reescritura |
| Agente `arquitecto` | Nombra al culpable por id y enlaza cada revelación con los personajes cuyo secreto destapa |
| Agente `trazador` | Sus fichas marcan las escenas en analepsis y las pistas falsas que se desmontan; su plan pasa `validar-plan` |
| Agente nuevo `sonda` | Responde quién es el culpable sin conocer el misterio |
| Operador humano | Resuelve las intervenciones que escriben `gate`, `sonda`, `auditar --acto` y `trayectoria` |

## 4. Contexto y restricciones

- **Invariantes que aplican.** El **1**: nada nuevo escribe `estado.db`, y por eso la cuenta de intentos vive en `harness.log` y no en `cursor.intento` (§5.5). El **3** y el **4**: el secreto y el fair play ganan medida directa. El **5**: la trayectoria y las decisiones de gate se escriben en `runs/`. El **6**: todo fichero nuevo se escribe con `plataforma/atomic.py`. El **7**: la política de cuota deja de reescribir capítulos cerrados. El **8**: los subcomandos nuevos toman el lock como los demás.
- **Restricciones técnicas.** El CLI no llama a modelos (0001 RNF-03). Las sondas y la calibración del juez son invocaciones de agente desde el orquestador o desde un script de release; el CLI solo compara sus salidas con el canon.
- **Supuestos verificados** en Claude Code 2.1.281, el 2026-09-24:
  - Una compactación deja en el transcript una entrada `{"type":"system","subtype":"compact_boundary","compactMetadata":{"trigger":…,"preTokens":…}}`, seguida de un mensaje de usuario con `isCompactSummary: true`. Se forzó con `/compact` en una sesión desechable. Solo se observó `trigger: "manual"`.
  - Cada resultado de `Task` en el transcript principal lleva `toolUseResult` con `agentType`, `resolvedModel` (`claude-opus-5-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001` en `humo-0003`), `content` (el informe del agente, sin la nota que Claude Code antepone en `message.content`) y `totalTokens`.
  - Un mensaje de asistente puede ocupar varias líneas del transcript con el mismo `message.id` y el mismo `usage`.
  - La entrada del hook `Stop` trae `session_id`, `transcript_path` y `hook_event_name`: la lee el plugin de Langfuse, que trazó cada sesión de `humo-0003`.
  - Un `Bash` que sale con un código distinto de 0 deja un `tool_result` con `is_error: true` cuyo texto empieza por `Exit code N`. Con 0, `toolUseResult.stdout` trae la salida, y la de `novela briefing` nombra `runs/<run_id>/briefings/…`.
  - Ninguno de estos cinco supuestos es contrato de Claude Code (`validators.md` §5.10).
- **Supuesto no verificado.** Una novela de humo de tres capítulos basta para dar un primer valor a los umbrales, que se revisan con la primera novela completa.
- **Dependencias.** Las specs 0001 y 0003, implementadas. El ADR 0002 (`novela gate`), aceptado con esta versión.

## 5. Propuesta

Seis fases. Al final de cada una la suite está en verde y el bucle sigue funcionando: las fases 1 y 2 endurecen gates existentes sin tocar el procedimiento, y la 3 cambia el procedimiento de una vez.

### 5.1 Fase 1 — gates mecánicos sobre capítulo y delta

Lo que se comprueba sin agentes nuevos ni cambios de procedimiento, salvo `validar --final`.

1. **Pistas y pistas falsas con cita** (RF-05). En el frontmatter, `pistas_plantadas` y `pistas_pagadas` pasan a ser listas de `{id, cita}`, y aparece `pistas_falsas_desmontadas: [{id, cita}]`. La ficha de plan gana `pistas_falsas_a_desmontar`, y el briefing del `escritor` las incluye en «Pistas de este capítulo» con su contenido.
2. **Cruce con el plan por igualdad** (RF-09, P-17). Los conjuntos del frontmatter son iguales a los de la ficha: pistas plantadas, pistas pagadas, pistas falsas desmontadas, hilos abiertos e hilos cerrados. Y una pista pagada tiene que estar plantada antes o en el mismo capítulo.
3. **Cita obligatoria en el delta** (RF-06, P-03) en `linea_temporal`, `conocimiento` y `conocimiento_lector`, además de en `libro_de_hechos`. La obligatoriedad está en el contrato del delta, no en el del estado: las filas ya aplicadas de `humo-0003` siguen leyéndose.
4. **Invariantes narrativos en `aplicar-delta`** (RF-07, P-06).
5. **Resúmenes acotados** (RF-08, P-07).
6. **Léxico vetado en `validar --final`** (RF-10, P-08). `canon/estilo.md` gana `lexico_vetado`, una lista de expresiones literales. `prohibiciones` sigue siendo descriptiva y es del juicio del `editor-estilo`.
7. **Huella estilométrica** (RF-11, P-09). La registra `validar` en `qa/NN-validacion.json`; es una señal, no un gate.
8. **Score `estilo` desde la huella** (RF-12).

### 5.2 Fase 2 — el secreto en el briefing

1. **Culpable por id** (RF-01, P-04). `canon/misterio.md` gana `culpable: PersonajeId`, obligatorio. Cada revelación y cada giro ganan `destapa: [PersonajeId]`, que por defecto es una lista vacía.
2. **Filtro por campo** (RF-01). `novela briefing` quita `secreto` y `coartada_y_cronologia_privada` de las fichas de personaje del `escritor`, del `editor-estilo` y de la `sonda`, salvo que alguna revelación o giro con `capitulo_previsto ≤ N` lo nombre en `destapa`.
3. **Solape con lo no revelado** (RF-02) sobre los mismos tres briefings.
4. **Briefing de reintento del `escritor`** (RF-03, P-05). El `escritor` deja de leer `qa/`: en reintento, `novela briefing` escribe `NN-escritor-intento-K.md` con la receta completa y una capa `reintento` con el QA saneado.

### 5.3 Fase 3 — el plan y los gates en código

1. **`novela validar-plan <slug>`** (RF-14, P-10) como gate del `trazador` en `/novela-nueva`.
2. **`novela gate <slug> <cap> <plan|mecanico|final|revision|delta>`** (RF-19, P-02, ADR 0002). Decide, cuenta, registra e interviene.
3. **Banda y tendencia de tensión** (RF-16) y **gancho con cita** (RF-17, P-11), en el gate de revisión.
4. **Código 5** (RF-29): intervención escrita por el CLI.
5. **Procedimientos.** `/novela-continuar` y `/novela-nueva` dejan de contar intentos y de escribir `intervencion.md`: llaman a `novela gate` y obedecen su código.

### 5.4 Fase 4 — tensión y secreto a escala de acto

1. **Carga de preguntas abiertas** en cada `checkpoint` (RF-15).
2. **`novela auditar <slug> --acto K`** (RF-18) en cada frontera de acto.
3. **Agente `sonda` y `novela sonda <slug> <cap> <briefing|texto>`** (RF-04, P-12). El `lector-suspense` deja de puntuar la previsibilidad (5.4.5 de la v0.2), que pasa a darla la sonda del texto.

### 5.5 Fase 5 — trayectoria del orquestador

1. **`novela trayectoria`**, invocado por un hook `Stop` (RF-20, P-13). Recorre el transcript y escribe `runs/<run_id>/trayectoria-NN.json`. Con violaciones, escribe `intervencion.md`.
2. **Modelo resuelto** (RF-13, P-14), leído de `toolUseResult.resolvedModel`.
3. **Contexto y compactación** (RF-22).
4. **Freno en `pendiente`** (RF-21).
5. **Política de cuota** (RF-24, P-15).

### 5.6 Fase 6 — verificación de release y novela de humo

1. **Control negativo de revisores** (RF-25) y **calibración del juez** (RF-26): fixtures versionados y un script de release que llama a modelos, fuera de `pytest`.
2. **Canario del orquestador** (RF-27).
3. **Novela de humo `humo-0002`**: primer baseline con todos los gates de esta spec, y calibración de los umbrales provisionales (§13).

## 6. Requisitos funcionales

| Id | Requisito | Prioridad | Fase |
|---|---|---|---|
| RF-01 | `novela briefing` excluye `secreto`, `coartada_y_cronologia_privada`, `arco_previsto` e `identidad.rol_narrativo` de las fichas de personaje en los briefings del `escritor`, el `editor-estilo` y la `sonda`, salvo que una revelación o un giro con `capitulo_previsto ≤ N` nombre a ese personaje en `destapa`. `Misterio` gana `culpable: PersonajeId`, y `Revelacion` y `Giro`, `destapa: list[PersonajeId] = []` | debe | 2 |
| RF-02 | `novela briefing` sale con 1 sin escribir el fichero si el briefing del `escritor`, el `editor-estilo` o la `sonda` comparte un bloque de 5 palabras con el conjunto secreto de N (§8.4). El mensaje nombra la capa, nunca el texto. En el briefing de la `sonda`, la capa de capítulos no se mira, ni con este filtro ni con el guardarraíl literal: es lo que la sonda mide | debe | 2 |
| RF-03 | En reintento, `novela briefing <slug> <cap> escritor` escribe `runs/<run_id>/briefings/NN-escritor-intento-K.md` con la receta completa y una capa `reintento`. De `qa/NN-validacion.json` y `qa/NN-gate-revision.json` entran los hallazgos completos. De `qa/NN-continuidad.json` y `qa/NN-suspense.json`, solo `tipo`, `gravedad`, `referencia` y `ubicacion`, y se descartan los hallazgos cuya referencia es un `rev-`, un `pfa-`, el `culpable` o una `pis-` ajena a la ficha del capítulo. Una referencia `hec-` se completa con `texto` y `cita` del libro de hechos. `NN-escritor.md` no se toca | debe | 2 |
| RF-04 | `novela sonda <slug> <cap> <briefing\|texto>` aplica la cadencia de §8.1: sale con 0 si no toca o no hay fuga, con 1 si faltan votos válidos y con 5 si la moda de los tres votos acierta el `culpable` antes de tiempo, con una mediana de confianza ≥ 0,5 en los votos que forman la moda. Escribe `qa/NN-sonda-<tipo>.json` | debe | 4 |
| RF-05 | `validar` exige que cada entrada de `pistas_plantadas`, `pistas_pagadas` y `pistas_falsas_desmontadas` lleve una `cita` de 15 caracteres o más que sea subcadena del cuerpo. Los dos lados se normalizan como en 0001 RF-33. El hallazgo de una cita ausente la copia en su `descripcion`: tras `validar --final`, el `editor-estilo` reintenta con su mismo briefing, que no trae las pistas, y solo así puede restaurar la frase que borró | debe | 1 |
| RF-06 | `aplicar-delta` rechaza un delta con una entrada sin `cita`, o con una de menos de 15 caracteres tras normalizar, en `linea_temporal`, `conocimiento`, `conocimiento_lector` o `libro_de_hechos`. No hay exención para el conocimiento inferido ni para el tiempo implícito. En `humo-0003`, 1 de 85 citas tenía menos | debe | 1 |
| RF-07 | `aplicar-delta` rechaza un delta que viola cualquiera de los invariantes narrativos de §8.3 | debe | 1 |
| RF-08 | `aplicar-delta` rechaza un resumen con un id que no esté en el delta, en la ficha del capítulo ni en el canon, o con un nombre propio (§8.3) que no aparezca en el cuerpo del capítulo ni entre los nombres del canon | debería | 1 |
| RF-09 | `validar` exige igualdad de conjuntos entre el frontmatter y la ficha: pistas plantadas, pistas pagadas, pistas falsas desmontadas, hilos abiertos e hilos cerrados. Toda pista pagada está plantada en un capítulo anterior o en este | debe | 1 |
| RF-10 | `validar --final` rechaza el capítulo si contiene una entrada de `canon/estilo.md` `lexico_vetado`, sin distinguir mayúsculas y con límites de palabra. Sin `--final` no la busca | debe | 1 |
| RF-11 | `validar` calcula la huella de §8.5 y la escribe en el campo `huella` de `qa/NN-validacion.json`, con los rasgos fuera de tolerancia. La huella nunca produce un hallazgo ni cambia el veredicto | debería | 1 |
| RF-12 | `checkpoint` emite el score `estilo` como la fracción de rasgos medidos que están dentro de tolerancia en la huella de la última `qa/NN-validacion.json`. Deja de leerlo de `qa/NN-estilo.json` | debería | 1 |
| RF-13 | `trayectoria-NN.json` registra el modelo resuelto del orquestador (`message.model`) y el de cada agente (`toolUseResult.resolvedModel`). Si el de algún agente o el del orquestador difiere del de la trayectoria anterior más reciente en la que ese agente aparece, `novela trayectoria` lo registra como violación | debería | 5 |
| RF-14 | `novela validar-plan <slug>` comprueba sobre `plan/` y `canon/` lo de §8.2 y escribe `qa/plan-validacion.json`. Sale con 0 si no hay hallazgos y con 1 si los hay | debe | 3 |
| RF-15 | `checkpoint` calcula la carga de preguntas abiertas —hilos abiertos, pistas plantadas sin pagar y revelaciones y giros con `capitulo_previsto > N`— y la emite como score `carga_preguntas`. Escribe un `aviso` en `harness.log` si la carga es 0 con N anterior al clímax, o si carga(N) < carga(N−1) < carga(N−2) < carga(N−3) con N−2, N−1 y N en el acto 2 | debería | 4 |
| RF-16 | `novela gate … revision` reintenta si `\|tension − curva_tension_objetivo[N]\| > banda_tension`, e interviene si la desviación es negativa en N y en los dos capítulos anteriores, todos con valor | debe | 3 |
| RF-17 | `novela gate … revision` exige que `qa/NN-suspense.json` traiga `gancho: {tipo, cita}`: la `cita` es subcadena de la última escena del capítulo incrustado en el briefing del `lector-suspense`, y el `tipo` es el `gancho_final` de la ficha. Una cita que no es subcadena hace ilegible el informe; un tipo distinto es un hallazgo `gancho_fuera_de_plan` | debería | 3 |
| RF-18 | `novela auditar <slug> --acto K` escribe `qa/acto-K.json` con los hallazgos definitivos de §8.6, y marca como hueco cada capítulo sin `tension_real` sin interpolarlo. Con algún hallazgo de gravedad alta, escribe `intervencion.md` y sale con 5 | debe | 4 |
| RF-19 | `novela gate <slug> <cap> <plan\|mecanico\|final\|revision\|delta>` sale con 0 para avanzar, 1 para reintentar o 5 para intervenir, según §8.1. Cuenta los intentos en `harness.log` del run, escribe `intervencion.md` al intervenir y se niega a un cuarto intento | debe | 3 |
| RF-20 | `novela trayectoria`, invocado por el hook `Stop`, escribe `runs/<run_id>/trayectoria-NN.json` con las comprobaciones de §8.7 para cada capítulo que la sesión tocó, y `intervencion.md` si hay violaciones. Sin `NOVELA_SESSION_ID` en el entorno, no hace nada y sale con 0 | debe | 5 |
| RF-21 | `novela pendiente` sale con 5 si existe un `intervencion.md` sin línea `resuelto:` en cualquier run, o si al último capítulo cerrado le falta `trayectoria-NN.json` y lo cerró una sesión distinta de `NOVELA_SESSION_ID` | debe | 5 |
| RF-22 | La trayectoria registra el máximo de tokens de contexto por turno de la sesión principal, con aviso por encima de 70.000, y cuenta como violación una compactación dentro del tramo de un capítulo | debería | 5 |
| RF-23 | *Fuera de esta spec (P-16).* `novela budget` y el nivel de degradación registrado en el manifiesto | — | — |
| RF-24 | `architecture.md` §9 no describe ningún nivel de degradación que omita un agente o lo ejecute sobre un capítulo cerrado. Sin `novela budget`, la única política es la parada limpia en checkpoint, y la trayectoria cuenta como violación cualquier agente del bucle que falte en un capítulo cerrado | debe | 5 |
| RF-25 | `backend/tests/revisores/` tiene fixtures con defecto sembrado (contradicción con el libro de hechos, pista pagada sin plantar, léxico vetado y ritmo fuera de tolerancia) y sin defecto, y un script de release que da la tasa de detección y de falsos positivos por revisor | debería | 6 |
| RF-26 | El mismo script calibra al `lector-suspense` con dos capítulos fixture, uno plano y otro de tensión alta. Sale en rojo si el plano recibe 6 o más o si la separación es menor que `banda_tension` | debería | 6 |
| RF-27 | El canario del orquestador comprueba, con un revisor impostor de `--agents`, que `novela gate` rechaza un `qa/` rechazado que el agente reporta como aprobado y que la trayectoria marca la lectura de `capitulos/` si la sesión obedece un informe que la invita | debería | 6 |
| RF-28 | La ficha de plan gana `pistas_falsas_a_desmontar: list[PistaFalsaId]` y, en cada escena, `analepsis: bool = False` | debe | 1 |
| RF-29 | El código de salida 5 significa «intervención escrita por el CLI». Lo emiten `gate`, `sonda`, `auditar --acto` y `pendiente`, y los procedimientos lo tratan como parada sin escribir nada | debe | 3 |
| RF-30 | Nuevo agente `sonda`, con `tools: Read, Write` y `model: sonnet`. Escribe solo `qa/NN-sonda-(briefing\|texto)-[1-3].json`. El hook conoce su salida, y su regla 5 admite ocho roles más `canario` | debe | 4 |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | `validar` por debajo de 2 s para 4.000 palabras, con la huella y el léxico vetado. `validar-plan` por debajo de 5 s para 24 fichas. `trayectoria` por debajo de 5 s para un transcript de 10 MB |
| RNF-02 | Consumo de contexto | La capa `reintento` estima menos de 3.000 tokens y cuenta en el presupuesto del `escritor` como cualquier otra. Lo que imprimen `gate`, `sonda`, `validar-plan` y `auditar --acto` cabe en 3 líneas. La trayectoria no entra en ningún briefing |
| RNF-03 | Coste / cuota | Cero llamadas a modelo desde el CLI. Las sondas son 3 llamadas a sonnet por punto de la cadencia (§8.1); con 24 capítulos en 3 actos son unas 30 llamadas por novela, frente a unas 170 del bucle |
| RNF-04 | Fiabilidad | `gate` y `trayectoria` son idempotentes ante una repetición: si la última línea de `harness.log` del run es del mismo gate con el mismo sha256 de entradas, repiten la decisión sin escribir línea ni contar intento. Cualquier otra orden del CLI entre las dos llamadas hace de la segunda un intento nuevo, aunque las entradas no hayan cambiado: un agente que no escribe nada gasta su intento. `sonda` cuenta siempre un voto ausente |
| RNF-05 | Observabilidad | `checkpoint` emite `estilo` (huella) y `carga_preguntas`. `novela sonda … texto`, que corre después del checkpoint, emite `previsibilidad`: la fracción de votos válidos que aciertan el culpable. `trayectoria` emite `trayectoria` (0 o 1, según haya violaciones) y `contexto_max` por el mismo `ScoreSink` |
| RNF-06 | Compatibilidad | No hay novelas empezadas. `humo-0003` está cerrada: su estado sigue leyéndose, porque la cita es obligatoria en el delta y no en el estado, pero sus frontmatters no validan contra el contrato nuevo. No se migra |
| RNF-07 | Seguridad | `trayectoria` solo lee el transcript que le da el hook y los de sus subagentes. En `runs/` escribe ids, nombres de herramienta, longitudes y cuentas, nunca el texto de un prompt, de un retorno o de un resultado de herramienta |

## 8. Interfaces y contratos

### 8.1 CLI

**Nuevos**

- `novela validar-plan <slug>` → 0 sin hallazgos, 1 con hallazgos (`qa/plan-validacion.json`, agente `validar-plan`).
- `novela gate <slug> <cap> <plan|mecanico|final|revision|delta>` → 0 avanzar, 1 reintentar, 5 intervenir. Qué lee cada uno y a quién reintenta el procedimiento:

  | Gate | Entrada | Aprueba si | Reintento |
  |---|---|---|---|
  | `plan` | `qa/plan-validacion.json` | sin hallazgos | `trazador` |
  | `mecanico` | `qa/NN-validacion.json` de `validar` | `veredicto: aprobado` | `escritor` |
  | `final` | `qa/NN-validacion.json` de `validar --final` | `veredicto: aprobado` y el informe dice `final: true` | `editor-estilo` |
  | `revision` | `qa/NN-continuidad.json`, `qa/NN-suspense.json`, la ficha, la curva y `tension_real` | ninguno `rechazado` ni ilegible, tensión en banda y gancho correcto (RF-16, RF-17) | `escritor` |
  | `delta` | cursor de `estado.db` y la última línea `aplicar-delta NN` del log | cursor en `(N, aplicar-delta)` | `cronista` |

  Reglas comunes:
  - **Ilegible es rechazado.** Un informe es ilegible si no existe, no valida contra `InformeQA` o es más antiguo que el briefing de su agente en el run. Un `qa/NN-suspense.json` sin `puntuaciones.tension` o sin `gancho` también lo es. `qa/NN-validacion.json` no tiene briefing: para `mecanico` y `final` es ilegible si su `capitulo_sha256` no es el del capítulo en disco. Un informe ilegible del `lector-suspense` reintenta al `escritor`: se pierde un intento, pero nunca se aprueba sin veredicto.
  - **Cuenta.** Los intentos consumidos de un gate son sus líneas `gate NN <tipo> -> 1` en el `harness.log` del run posteriores a la última línea `gate NN <tipo> -> 5 · intervención` de ese mismo gate. Con dos, el siguiente rechazo sale con 5. Una intervención resuelta concede así otros tres intentos, que es lo que necesitó el capítulo 3 de `humo-0003`. Cada gate cuenta aparte: los fallos del `escritor` y los del `editor-estilo` no se suman.
  - **Intervención viva.** Con un `intervencion.md` vivo en el run, sale con 5 sin evaluar nada. Escribe la línea `gate NN <tipo> -> 5 · intervención viva`, que no reinicia ninguna cuenta.
  - **Repetición** (RNF-04). Si la última línea del log es del mismo gate con el mismo sha256 de entradas, repite la decisión sin escribir línea. Cualquier otra orden en medio hace de la llamada un intento nuevo.
  - **Custodia.** Una causa de `aplicar-delta` que empieza por `custodia:` sale con 5 sin reintento.
  - **Lo que autoriza una resolución.** Una intervención resuelta por una causa que no es el agotamiento de intentos, como la tendencia negativa, autoriza esa causa en ese capítulo: el gate no vuelve a intervenir por ella, y sí puede reintentar o intervenir por otra.
  - **Rango.** Sobre un capítulo cerrado, o por delante del siguiente al último checkpoint, sale con 2 sin abrir run.
  - El gate `revision` escribe sus propios hallazgos (banda, gancho) en `qa/NN-gate-revision.json`, con agente `gate`.
- `novela sonda <slug> <cap> <briefing|texto>` → 0 no toca o sin fuga, 1 faltan votos, 5 fuga. Cadencia, con R el menor `capitulo_previsto` de las revelaciones y giros que nombran al `culpable` en `destapa` (sin ninguna, el mayor `capitulo_previsto`):
  - `briefing`: N < R y N es el primer capítulo de un acto o su ficha paga una pista de una revelación que destapa al culpable. La sonda lee `NN-escritor.md` del run. Corre antes del primer `escritor` del capítulo, no en los reintentos.
  - `texto`: N es el último capítulo de un acto o N = R − 1. Con 1, el comando escribe antes `runs/<run_id>/briefings/NN-sonda.md` (receta `sonda`: capítulos del acto en curso hasta N y el reparto, sin misterio).
  - Acierto: la moda de los tres votos es el `culpable` y la mediana de `confianza` de los votos que forman la moda es ≥ 0,5. Sin moda, no hay acierto. Un acierto de la sonda del briefing es fuga (5). Uno de la sonda del texto con N < R − 1, también (5). En N = R − 1, el acierto es lo esperado, y **no** acertar es un hallazgo `pista_sin_efecto` que no para (0).
  - Un voto es inválido si no valida contra `sonda-voto.schema.json` o es más antiguo que el briefing que juzga (`NN-escritor.md` o `NN-sonda.md`). Con dos líneas `sonda NN <tipo> -> 1` en el log, el siguiente voto ausente o inválido sale con 5.
  - Una fuga resuelta autoriza esos votos: con los mismos votos, sale con 0. Si el operador cambió la ficha o el plan, regenera el briefing, los votos quedan obsoletos y la sonda vuelve a correr.
- `novela trayectoria [--transcript <ruta>]` → sin argumento lee la entrada del hook `Stop` por stdin. Sale con 0 salvo uso incorrecto; su resultado está en disco.

**Modificados**

- `novela validar <slug> <cap> [--final]`: `--final` activa el léxico vetado (RF-10) y deja `final: true` en `qa/NN-validacion.json`. El paso 5 del procedimiento lo usa, y su gate es `final`.
- `novela auditar <slug> [--acto K]` (RF-18).
- `novela briefing`: reintento del `escritor` (RF-03), filtro y solape (RF-01, RF-02) y agente `sonda`.
- `novela pendiente`: código 5 (RF-21).
- `novela checkpoint`: `estilo` desde la huella, y `carga_preguntas` (RF-12, RF-15).
- `plataforma/salida.py`: `INTERVENCION = 5` en la tabla de códigos (RF-29).

### 8.2 `validar-plan`

1. **Fair play.** Toda revelación y todo giro tienen al menos una pista de `pistas_que_la_pagan` con `capitulo_plantado < capitulo_previsto`, y la ficha de ese capítulo la tiene en `pistas_a_plantar`.
2. **Ids.** Todo id de una ficha existe: personajes con ficha, escenarios de `mundo.md`, pistas, pistas falsas, e ids de escena del propio capítulo. `culpable` y cada `destapa` son personajes con ficha.
3. **Orden de pistas.** Cada pista está en `pistas_a_plantar` de la ficha de su `capitulo_plantado` y en `pistas_a_pagar` de la de su `capitulo_pagado`, con plantado antes que pagado. Cada pista falsa con `cuando_se_desmonta` está en `pistas_falsas_a_desmontar` de esa ficha.
4. **Hilos.** Cada hilo se abre una sola vez y se cierra como mucho una, después de abrirse.
5. **Solape.** El texto de cada ficha N no comparte bloques de 5 palabras con el conjunto secreto de N (§8.4).
6. **Curva.** `curva_tension_objetivo[climax]` es el máximo. Si `punto_medio > 1`, su valor supera al del capítulo anterior y no es menor que el del siguiente, salvo que el siguiente sea el clímax. En los actos 2 y siguientes no hay más de `max_capitulos_sin_subir` capítulos seguidos con un valor que no supera al anterior.

### 8.3 Invariantes del delta y resúmenes

Invariantes narrativos (RF-07):

1. **El muerto no resucita.** Un personaje con `condicion: muerta` en el estado no cambia de condición, salvo que una revelación o un giro con `capitulo_previsto = N` lo nombre en `destapa`.
2. **El muerto no aprende.** No gana entradas de `conocimiento` con `desde_capitulo = N`, salvo que la ficha tenga una escena con `analepsis: true` en la que esté presente.
3. **Ubicaciones del canon.** Toda `ubicacion` de `personajes` y de `objetos` es un escenario de `canon/mundo.md`. En `humo-0003` esto habría rechazado los tres deltas: sus ubicaciones (`esc-torre-faro`, `esc-rampa-puerto`, `esc-casa-faro`, `esc-bar-opairo`) no son ninguno de los cuatro escenarios del canon, que las fichas del plan sí usan.
4. **Personajes del canon.** Todo personaje del delta tiene ficha en `canon/personajes/`: claves de `personajes` y de `conocimiento`, `de` y `a` de `relaciones` y `poseedor` de `objetos`. En `humo-0003` esto habría rechazado a `per-anselmo`.
5. **Hilos.** Solo se cierra un hilo abierto en el estado o que se abre en el mismo delta.
6. **Punto de vista.** Con `punto_de_vista` `primera_persona` o `tercera_limitada`, cada hecho que el personaje POV aprende en N está en `conocimiento_lector` con `desde_capitulo = N`. Con `multiple` o `narrador_no_fiable` no se comprueba.

Resúmenes (RF-08). Los textos son `linea`, `parrafo` y cada valor de `escena`. Un **id** es cualquier subcadena con la forma de un id de `architecture.md` §5. Un **nombre propio** es una palabra de tres letras o más que empieza por mayúscula y no es la primera de su frase, sea tras `.`, `!`, `?`, `…` o `:`, o al principio del texto. Los **nombres del canon** son las palabras de `nombre` y `alias` de las fichas y de `nombre` de escenarios e instituciones. Sobre los tres resúmenes de `humo-0003`, 74 candidatos y 0 falsos positivos.

### 8.4 Conjunto secreto de N

Lo que ni el `escritor`, ni el `editor-estilo`, ni la `sonda` pueden tener delante en el capítulo N:

- `verdad_oculta`, `culpable_o_amenaza` y los tres campos de `motivo_medio_oportunidad`, mientras N sea menor que el mayor `capitulo_previsto` de revelaciones y giros;
- `contenido` de las revelaciones y los giros con `capitulo_previsto > N`;
- los textos de los campos que RF-01 filtra en los personajes no destapados: `secreto.que_oculta`, el `detalle` de cada momento de `coartada_y_cronologia_privada`, `arco_previsto` e `identidad.rol_narrativo`.

Un bloque son 5 palabras seguidas (secuencias `\w+` tras NFC y minúsculas) con al menos dos de cuatro letras o más. Un bloque que aparece también en un texto permitido en N no cuenta, porque ya es público. Son permitidos los textos que exime el guardarraíl literal (`assemble._permitidos`: las pistas plantadas o de la ficha y lo ya revelado) y el contenido de las revelaciones y los giros con `capitulo_previsto ≤ N`. Así, la ficha del capítulo de una revelación puede compartir palabras con `verdad_oculta`.

El tamaño del bloque y el mínimo de palabras largas son constantes con nombre. La tarea que implementa RF-02 mide los falsos positivos sobre las fichas y los briefings de `humo-0003`, y las sube si hay alguno. Lo hace en local, desde un test que lee el misterio y no imprime el texto.

### 8.5 Huella estilométrica

| Rasgo | Cómo se mide | Referencia | Tolerancia inicial |
|---|---|---|---|
| `longitud_media_frase` | palabras por segmento terminado en `.`, `!`, `?` o `…` | `ritmo.longitud_media_frase` | ±25 % relativo |
| `dispersion_frase` | desviación típica de lo anterior | — | se registra, sin tolerancia |
| `proporcion_dialogo` | palabras de líneas que empiezan por `—` sobre el total | `ritmo.proporcion_dialogo` | ±0,10 absoluto |
| `delta_burrows` | Delta de Burrows sobre una lista fija de palabras funcionales, con la media y la desviación de cada palabra calculadas sobre las escenas de los capítulos 1 a 3, y sin las palabras de desviación nula | escenas de 1–3 | ≤ 0,9, desde el capítulo 4 |

Las tolerancias van en `canon/estilo.md` `ritmo.tolerancias`, con estos valores por defecto. Contra `parrafos_canonicos` solo se calcula `delta_burrows` si suman 1.000 palabras o más. Datos de `humo-0003`: frase media de 7,9 a 8,4 frente a 15 (los tres fuera), diálogo de 0,27 a 0,31 frente a 0,30 (los tres dentro), Delta de Burrows de cada capítulo contra las escenas de los otros dos de 0,46 a 0,59, y contra las 119 palabras canónicas, 2,11. El umbral de 0,9 es 1,5 veces el máximo observado.

### 8.6 Auditoría de acto

`novela auditar --acto K` mira los capítulos cerrados hasta el último del acto y reporta solo lo que ya no puede cambiar:

| Hallazgo | Gravedad |
|---|---|
| Pista plantada cuyo `capitulo_pagado` ya pasó sin pagarse | alta |
| Revelación o giro con `capitulo_previsto` ya pasado sin pista plantada antes | alta |
| Pista falsa con `cuando_se_desmonta` ya pasado sin estar en `pistas_falsas_desmontadas` de ese frontmatter | alta |
| Hilo que la ficha cierra en un capítulo ya pasado y sigue abierto | alta |
| Capítulo sin `tension_real` (hueco) | media |
| `tension_real` fuera de banda | media |
| `delta_burrows` fuera de tolerancia en dos o más capítulos del acto | media |

### 8.7 Trayectoria

`runs/<run_id>/trayectoria-NN.json`, validado por `trayectoria.schema.json`. El tramo de un capítulo va desde la primera orden `novela` de la sesión que lo nombra hasta su `novela checkpoint`: una sesión reanudada no empieza por el `briefing` del `escritor`. Guarda una entrada por sesión, con clave `NOVELA_SESSION_ID`, que es el `sesion=` de `harness.log` y sobrevive a un `/clear`, y con el `session_id` del transcript como dato. Las sesiones de `/novela-nueva` no tienen tramo: su run es de arranque. La herramienta de subagentes se llama `Agent` en los transcripts de `humo-0003` y `Task` en la documentación, y se aceptan los dos nombres. El workspace se resuelve con el slug de las órdenes, no con el `cwd` del hook, que no está verificado.

- **Orden** (§4.10): cada invocación de subagente tiene antes, en el tramo, un `novela briefing` del mismo agente con código 0 (la `sonda` del briefing, el del `escritor`; la del texto, un `novela sonda … texto` con 1). `validar` va antes de los revisores y `validar --final` después del `editor-estilo`. `gate … revision` va antes del `cronista` y `aplicar-delta` antes de `checkpoint`. Tras el `checkpoint` del último capítulo de un acto van `novela sonda … texto` y `novela auditar --acto`.
- **Lo que no deja artefacto**: un `Read`, o una orden de `Bash` o de `PowerShell`, sobre `capitulos/` desde la sesión principal. El resto de lecturas de la sesión principal, como `checkpoints/latest.json` o la búsqueda de `intervencion.md`, son del procedimiento. Un `Write` o un `Edit` de la sesión principal en el workspace, se haya denegado o no, salvo `runs/*/intervencion.md`. Una invocación de un tipo que no es uno de los ocho. Un prompt de subagente de más de 2.000 caracteres (en `humo-0003`, el máximo fue 1.714, un reintento del `cronista` con su causa). Un retorno de más de 3 líneas no vacías o de más de 1.000 caracteres (`humo-0003`: 3 líneas y 712 como máximo). Un capítulo cerrado al que le falta alguno de los cinco agentes del bucle (RF-24).
- **Contexto**: el máximo de `input_tokens + cache_creation_input_tokens + cache_read_input_tokens` por mensaje de asistente distinto, sin repetir `message.id`. Por encima de 70.000 es aviso, y en `humo-0003` el máximo fue 46.676. Un `compact_boundary` dentro del tramo es violación.
- **Modelos** (RF-13).

### 8.8 Esquemas

Se regeneran los de `backend/schemas/` y cambian `definitions.md` y el test de contrato en el mismo commit que cada modelo.

| Esquema | Cambio | Tipo |
|---|---|---|
| `capitulo.schema.json` | pistas como `{id, cita}`, `pistas_falsas_desmontadas` | ruptura |
| `delta.schema.json` | `cita` obligatoria, de 15 caracteres o más, en `linea_temporal`, `conocimiento`, `conocimiento_lector` y `libro_de_hechos` | ruptura |
| `canon.schema.json` | `Misterio.culpable`, `destapa` en revelaciones y giros, `Estilo.lexico_vetado` y `Ritmo.tolerancias` | ruptura (`culpable` es obligatorio) |
| `plan-capitulo.schema.json` | `pistas_falsas_a_desmontar` y `EscenaPlan.analepsis` | compatible |
| `config.schema.json` | `parametros_sistema.banda_tension` (2) y `max_capitulos_sin_subir` (3) | compatible |
| `qa-informe.schema.json` | agentes `validar-plan`, `gate` y `sonda`, `huella`, `final`, `gancho` y los tipos de hallazgo nuevos | compatible |
| `sonda-voto.schema.json` | nuevo: `{schema_version, capitulo, tipo, voto, culpable_id: PersonajeId \| null, confianza}` | nuevo |
| `trayectoria.schema.json` | nuevo | nuevo |
| `state.schema.json` | sin cambios | — |

### 8.9 Contratos de agente y `.claude/`

- **Nuevo** `sonda` (RF-30).
- **Ruptura** `escritor`: citas en el frontmatter y, en reintento, solo su briefing de intento, sin `qa/`.
- **Compatibles**: `lector-suspense` (`gancho`, sin `previsibilidad`), `cronista` (cita en las cuatro colecciones y solo personajes con ficha y escenarios del canon, para lo que su receta gana `canon/mundo` y un reparto con `id`, `nombre` y `alias` de cada ficha, sin ningún otro campo), `arquitecto` (`culpable`, `destapa`, `lexico_vetado`), `trazador` (`pistas_falsas_a_desmontar`, `analepsis`).
- **Hook `PreToolUse`**: salida de `sonda` y regla 5 con ocho roles.
- **Hook `Stop`**: nuevo, `novela trayectoria`, registrado en `.claude/settings.json`. El del plugin de Langfuse sigue siendo suyo.
- **Procedimientos**: `/novela-continuar` y `/novela-nueva`, según §5.3.

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | `culpable`, `destapa`, `lexico_vetado`, `ritmo.tolerancias` |
| `plan/` | `pistas_falsas_a_desmontar` y `analepsis`; `validar-plan` lo verifica una vez |
| `estado/estado.db` | Sin cambios de forma. Nada nuevo lo escribe: `cursor.intento` sigue como está, y la cuenta de intentos vive en `harness.log` |
| `memoria/` | Sin cambios de forma; `aplicar-delta` valida el resumen antes de renderizarlo |
| `runs/` | `trayectoria-NN.json`, `NN-escritor-intento-K.md`, `NN-sonda.md` y las líneas `gate` y `sonda` de `harness.log` |
| `qa/` | `plan-validacion.json`, `NN-gate-revision.json`, `NN-sonda-<tipo>-K.json`, `NN-sonda-<tipo>.json`, `acto-K.json` |

## 10. Migración y compatibilidad

No aplica: no hay novelas empezadas. `humo-0003` está cerrada y no se migra (RNF-06). Las tres rupturas de §8.8 son de contratos de salida de agente, y el primer capítulo de una novela nueva ya las cumple o falla en su `validar`.

## 11. Criterios de aceptación

Los de `gates.py`, `violaciones.py`, `apply.py` y el ensamblado del briefing son property-based (`validators.md` §3.6).

- [ ] **CA-01** (RF-01) property-based: sobre canons y fichas generados, el briefing del `escritor`, el `editor-estilo` o la `sonda` nunca trae `secreto`, `coartada_y_cronologia_privada`, `arco_previsto` ni `rol_narrativo` de un personaje que ninguna revelación con `capitulo_previsto ≤ N` destapa, y sí los trae si alguna lo destapa
- [ ] **CA-02** (RF-02) property-based: un briefing del `escritor`, el `editor-estilo` o la `sonda` con un bloque del conjunto secreto de N hace salir a `briefing` con 1 sin escribir el fichero, y el mensaje no contiene el bloque; un briefing sin solape se escribe. Un bloque de cinco palabras de menos de cuatro letras no cuenta, ni uno que también está en un texto permitido en N. La capa de capítulos del briefing de la `sonda` no se mira
- [ ] **CA-03** (RF-03) property-based: con `qa/` generados, la capa `reintento` no contiene ninguna `descripcion` ni `correccion_sugerida` de continuidad o suspense, ni ningún hallazgo con referencia `rev-`, `pfa-`, `culpable` o `pis-` ajena a la ficha; contiene enteros los de `validar` y `gate`. `NN-escritor.md` queda con el mismo sha
- [ ] **CA-04** (RF-04) con votos fixture: moda correcta y mediana 0,5 en la sonda del briefing → 5 e `intervencion.md`; mediana 0,4 → 0; tres votos distintos → 0; un voto ausente → 1, y a la tercera vez → 5. Sonda del texto en R − 1 sin acierto → 0 con `pista_sin_efecto`. Fuera de la cadencia → 0 sin leer votos. Un voto más antiguo que su briefing cuenta como ausente. Con la fuga resuelta y los mismos votos → 0
- [ ] **CA-05** (RF-05) property-based: una pista plantada, pagada o falsa desmontada sin cita, con una cita de menos de 15 caracteres o con una que no es subcadena del cuerpo normalizado, nunca pasa `validar`. El hallazgo de una cita ausente contiene la cita
- [ ] **CA-06** (RF-06) property-based: un delta con una entrada sin cita, o con una cita de menos de 15 caracteres, en cualquiera de las cuatro colecciones nunca se aplica, y el estado queda igual. La base de `humo-0003` sigue leyéndose con `novela estado`
- [ ] **CA-07** (RF-07) property-based, un test por invariante de §8.3: el delta que lo viola se rechaza y el que lo respeta se aplica, con la excepción de `destapa` en el 1, la de `analepsis` en el 2 y la de `multiple` y `narrador_no_fiable` en el 6
- [ ] **CA-08** (RF-08) un resumen con un nombre propio ausente del cuerpo y del canon se rechaza; uno con el nombre al principio de la frase se acepta. Los tres resúmenes de `humo-0003`, contra sus capítulos y su canon, se aceptan
- [ ] **CA-09** (RF-09) property-based: si el frontmatter y la ficha difieren en cualquiera de los cinco conjuntos, o una pista se paga sin estar plantada, `validar` rechaza. Los tres frontmatters de `humo-0003`, con sus ids, cumplen la igualdad
- [ ] **CA-10** (RF-10) property-based: una entrada de `lexico_vetado` en el cuerpo rechaza `validar --final`, con cualquier combinación de mayúsculas, y no rechaza `validar`. Una entrada que solo aparece dentro de otra palabra no rechaza
- [ ] **CA-11** (RF-11) sobre un fixture de ritmo conocido, la huella da los valores esperados; una huella fuera de tolerancia deja el veredicto en `aprobado` y la lista sin hallazgos de huella. Mutación sobre las comparaciones con la tolerancia
- [ ] **CA-12** (RF-12) `calcular_scores` da `estilo` = 0,5 con dos rasgos medidos y uno fuera, y no lee `qa/NN-estilo.json`
- [ ] **CA-13** (RF-13) con dos transcripts fixture de capítulos seguidos y modelos distintos del `escritor`, la segunda trayectoria registra la violación `modelo_cambiado`
- [ ] **CA-14** (RF-14) sobre el plan de `humo-0003`, con `pistas_falsas_a_desmontar` completado desde su escaleta y un misterio sintético con su calendario (el suyo no tiene `culpable`), `validar-plan` sale con 0. Sobre planes generados, rompe con 1 cada una de las seis comprobaciones de §8.2 por separado. Mutación sobre las comparaciones de la curva
- [ ] **CA-15** (RF-15) con el estado de `humo-0003`, la carga es 12, 9 y 0; ninguna emite aviso. Una serie que baja tres veces en el acto 2 emite el aviso. Mutación sobre el umbral
- [ ] **CA-16** (RF-16) property-based: con `banda_tension` = 2, una desviación de 3 → 1; de −2 con las dos anteriores negativas → 5; un hueco en medio → no hay tendencia. Mutación sobre la banda
- [ ] **CA-17** (RF-17) un gancho cuya cita está en la última escena y cuyo tipo es el de la ficha → aprueba; una cita de otra escena → ilegible → 1; un tipo distinto → 1 con `gancho_fuera_de_plan` en `qa/NN-gate-revision.json`. La última escena empieza tras la última línea igual a `convenciones_formato.separador_escena`, `* * *` por defecto
- [ ] **CA-18** (RF-18) sobre un fixture con un hueco en `tension_real`, la auditoría de acto lo reporta como hueco y no devuelve valor para ese capítulo. Una pista con el pago vencido → 5 e `intervencion.md`
- [ ] **CA-19** (RF-19) con el agente falso, cada uno de los cinco gates: aprobado → 0; rechazado → 1 dos veces y 5 a la tercera, con `intervencion.md`; dos llamadas seguidas sin otra orden en medio → misma decisión con una sola línea; con otra orden en medio y las mismas entradas (un agente que no escribió nada) → cuenta otro intento; con una intervención viva → 5 sin reiniciar la cuenta; tras resolverla → otros tres intentos; un informe más antiguo que su briefing → rechazado; `custodia:` → 5 al primer fallo. Los rechazos de `mecanico` no consumen intentos de `final`. Una tendencia negativa resuelta no vuelve a intervenir en ese capítulo
- [ ] **CA-20** (RF-20) sobre transcripts fixture construidos desde los de `humo-0003`, cada comprobación de §8.7 produce su violación y el transcript limpio ninguna. Sin `NOVELA_SESSION_ID`, no escribe nada. La trayectoria no contiene ningún texto de prompt ni de retorno. Un transcript con `Agent` y otro con `Task` dan la misma trayectoria. Dos sesiones sobre un capítulo, una de ellas reanudada, no dan un agente ausente
- [ ] **CA-21** (RF-21) `pendiente` sale con 5 con un `intervencion.md` vivo, y con 0 si tiene `resuelto:`; con 5 si falta la trayectoria del último capítulo cerrado por otra sesión, y con 0 si lo cerró la sesión actual
- [ ] **CA-22** (RF-22) un transcript con `compact_boundary` dentro de un tramo marca la violación; uno con dos líneas del mismo `message.id` cuenta sus tokens una vez
- [ ] **CA-24** (RF-24) revisión en el commit: `architecture.md` §9 sin niveles 2 a 4 ni `novela budget`. Y un test: un capítulo cerrado sin el `lector-suspense` en el tramo es violación
- [ ] **CA-25** (RF-25, RF-26) los fixtures existen y validan contra sus esquemas, y el script tiene un modo en seco que no llama a modelos y comprueba su veredicto sobre salidas fixture (I + T)
- [ ] **CA-27** (RF-27) el canario del orquestador da verde en la novela de humo `humo-0002` (D)
- [ ] **CA-28** (RF-28) `plan-capitulo.schema.json` acepta una ficha sin los campos nuevos y con ellos
- [ ] **CA-29** (RF-29) test de contrato: los procedimientos nombran el código 5 y no escriben `intervencion.md` para los gates de `novela gate`. La siguen escribiendo para las paradas que el CLI no decide: el código 4, un 1 de `briefing` o de `checkpoint` y el gate del `arquitecto`
- [ ] **CA-30** (RF-30) test de contrato: ocho agentes; `sonda` con `Read, Write` y `sonnet`; `SALIDAS` del hook con su patrón; la regla 5 lo admite y deniega un noveno nombre

## 12. Trazabilidad

Se rellena durante la implementación.

| Requisito | Criterio | Test | Estado |
|---|---|---|---|
| RF-01 | CA-01 | | pendiente |

## 13. Verificación

- **Property-based**: RF-01, RF-02, RF-03, RF-05, RF-06, RF-07, RF-09, RF-10 y RF-16. Todo lo que toca `gates.py`, `violaciones.py` o el ensamblado.
- **Mutación**: las comparaciones de umbral de RF-11, RF-14, RF-15 y RF-16.
- **Model checking** (§4.10) ampliado con `novela gate`: la enumeración de transiciones pasa a llamar al gate real con el agente falso.
- **Contrato**: esquemas de §8.8, `.claude/agents/sonda.md`, hook y `settings.json` con el hook `Stop`.
- **Novela de humo `humo-0002`** (fase 6): primer baseline con esta spec, canario del orquestador y calibración. Los umbrales provisionales son siete: tolerancias de la huella, 0,9 de Burrows, `banda_tension` 2, `max_capitulos_sin_subir` 3, 70.000 de contexto, 2.000 y 1.000 caracteres de prompt y retorno, y 0,5 de confianza. Se revisan con la primera novela completa.
- **Riesgos aceptados**:
  - `validators.md` §5.12: las sondas son de la misma familia de modelo.
  - §5.13: los invariantes cubren lo que se puede escribir como regla. De los seis que proponía la v0.2 se descartan dos (§15), y entra el de personajes del canon.
  - El conocimiento inferido lleva cita obligatoria, pero la cita prueba que el pasaje existe, no que implique el hecho (§5.9).
  - `toolUseResult`, `compact_boundary`, el nombre `Agent` y la división de un mensaje en varias líneas no son contrato de Claude Code (§5.10). Si cambian, `trayectoria` falla cerrado: sin trayectoria, `pendiente` para.
  - §5.18: el orden por fecha de modificación, del que dependen la ilegibilidad de un informe y la de un voto, depende del reloj del sistema de ficheros.
  - §5.19: el `escritor` en reintento pierde la `descripcion` de los revisores. La tasa de éxito del segundo intento se mide en `humo-0002`.
  - §5.20: la tendencia negativa interviene con tres desviaciones de −1, que puede ser ruido del juez.
  - §5.21: una sesión del harness sin `NOVELA_SESSION_ID` escapa a la trayectoria, y `pendiente` no se la exige.
  - §5.22: `humo-0003` se lee solo en parte tras las rupturas.
  - §5.23: la huella no es gate. Una deriva de estilo sigue pasando el bucle, solo que ahora consta y puntúa.
  - El catálogo de fallos de esta spec es `validators.md` §4.18 (F-80 a F-168).

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | Ninguno se toca. El 1 se preserva explícitamente: la cuenta de intentos no entra en `estado.db` (ADR 0002). El 3 gana medida directa (sondas) y dos filtros; el 7 deja de chocar con la política de cuota |
| Esquemas | Los de §8.8. Se regeneran y se actualiza `definitions.md` en el commit de cada uno |
| Contratos de agente | Un agente nuevo y cinco contratos modificados (§8.9) |
| CLI | Cuatro subcomandos nuevos y cinco modificados (§8.1). `AGENTS.md` «CLI» y `architecture.md` §8 |
| Docs de referencia | `AGENTS.md`: ocho roles, CLI. `CLAUDE.md`: bucle por capítulo, ocho subagentes, hooks. `architecture.md`: §2.1 (quién decide los gates), §2.3, §6.2 y §6.3 (filtro, solape y reintento), §7.2 (frontmatter), §7.3 (QA), §7.4 y §7.5 (`sonda`), §7.6 (cita obligatoria), §8, §9 y §10 (scores nuevos). `validators.md`: §2, §3.9, §4.4, §4.13, §4.15, §4.16, §4.17 (F-06, F-08, F-25, F-31, F-33, F-34, F-35 y F-53) y §6, al estado real. `definitions.md`: canon, plan, QA y artefactos |
| ADR | 0002 — los gates los decide el CLI |
| Frontend | Nada en esta spec. La trayectoria, la carga de preguntas abiertas y la huella son candidatas al panel |

## 15. Alternativas descartadas

- **Meterlo todo en la 0001.** La 0001 está aceptada y no admite preguntas abiertas (`_plantilla.md` §16).
- **Partir esta spec en cuatro** (P-01). Las fases comparten modelos (`InformeQA`, `FrontmatterCapitulo`, `Misterio`) y el procedimiento cambia una sola vez, en la fase 3. Cuatro specs obligarían a enmendar el procedimiento cuatro veces. Las fases del plan dan la misma entrega incremental.
- **Detectar la paráfrasis con embeddings.** Añade una dependencia de modelo local para algo que la sonda mide directamente.
- **Que el `lector-suspense` juzgue la previsibilidad.** Conoce la solución.
- **Comparar el estilo con el capítulo anterior.** Una deriva gradual pasa cualquier comparación entre vecinos.
- **Contar los intentos en `cursor.intento`** (P-02). Obliga a `novela gate` a escribir `estado.db`, que el invariante 1 reserva a `aplicar-delta`. `harness.log` ya es el registro por run, y leerlo desde código resuelve lo que falló en la sesión (F-31).
- **Un fichero de decisiones aparte, `gates.jsonl`.** Sería un segundo registro con la misma información que las líneas de `harness.log`.
- **`inferido: true` para exentar la cita** (P-03). Una puerta que un modelo barato usaría de más. En `humo-0003`, las 51 entradas de `conocimiento` y `conocimiento_lector` llevaban cita.
- **Tipar `prohibiciones` en `literal` y `descriptiva`** (P-08). Las seis de `humo-0003` son descriptivas («Nada de metáforas acumuladas…»). Un campo nuevo, `lexico_vetado`, es aditivo y no cambia el tipo de una colección append-only.
- **Léxico vetado en el primer `validar`.** Un término vetado reintentaría al `escritor`, que es opus, para algo que el `editor-estilo` corrige de todos modos.
- **La huella como gate.** Con un solo baseline, fallaría en los tres capítulos de `humo-0003` por la longitud de frase, y la tolerancia no tiene todavía un dato detrás.
- **Delta de Burrows contra `parrafos_canonicos`.** Con 119 palabras, da 2,11 frente a 0,46–0,59 entre capítulos: es ruido.
- **Solape de escenas en `linea_temporal`.** `inicio` es texto libre: en `humo-0003` aparecen «23:10», «mañana» y «tarde/noche (durante temporal)», sin día. Exigiría un tiempo diegético estructurado, y eso es otra spec.
- **Objeto de relevancia alta sin poseedor ni ubicación.** En `humo-0003`, `obj-004` está así con toda legitimidad: nadie sabe dónde está, y en una novela de misterio eso es trama. El modelo ya distingue ese caso (`definitions.md` §4).
- **Filtrar solo los secretos marcados como del misterio** (P-04). Si el `arquitecto` marca mal el del culpable, la fuga es total. Filtrar todos por defecto falla cerrado: el `escritor` pierde subtexto hasta la revelación, y no la solución.
- **Una `sonda` sin herramientas** (P-12). El orquestador tendría que meter el briefing en el prompt, y con él 60.000 tokens en su propio contexto.
- **La sonda con haiku.** Es una cota inferior de la fuga (§5.12): una sonda débil que no acierta no prueba nada.
- **Que la trayectoria sea un script de la stdlib en `.claude/hooks/`.** La lógica tiene ramas que merecen TDD y tipos, y el hook `Stop` puede invocar `novela` como invoca el bucle.
- **Leer el modelo de los transcripts de subagente** (P-14). `toolUseResult.resolvedModel` da lo mismo desde el transcript principal, por invocación y sin abrir otros ficheros.
- **`novela budget` en esta spec** (P-16). La 0001 lo aplazó por falta de datos, y la novela de humo tampoco los da: un capítulo por sesión nunca se acercó al límite.
- **Hacer el editor en lote antes del `cronista`** (P-15). Retrasa el delta de tres capítulos, y el `escritor` del siguiente trabaja sin su estado.

## 16. Preguntas abiertas

Ninguna. La v0.2 tenía diecisiete. Se cerraron el 2026-09-24 con los datos de `humo-0003` (sus deltas, su estado, sus capítulos medidos por script, sin volcar prosa, y los transcripts de sus sesiones), con una compactación forzada en Claude Code 2.1.281 y con las decisiones del autor.

| Pregunta | Decisión | Evidencia | RF |
|---|---|---|---|
| P-01 una o varias specs | Una, en seis fases | Comparten modelos y el cambio de procedimiento | — |
| P-02 `novela gate` | Sí. Cuenta en `harness.log`, no en `estado.db`. ADR 0002 | F-31 en el capítulo 3 | RF-19, RF-29 |
| P-03 cita con conocimiento inferido | Obligatoria siempre, sin exención | 51 de 51 entradas de conocimiento con cita; el delta del capítulo 2 sin citas en `linea_temporal` | RF-06 |
| P-04 qué secretos y cómo enlazarlos | Todos se filtran; `destapa` en revelación y giro; `culpable` por id | — | RF-01, RF-02 |
| P-05 criterio del QA saneado | Lista blanca de campos y descarte por referencia; `descripcion` y `correccion_sugerida` se pierden en continuidad y suspense; `hec-` se completa desde el estado | — | RF-03 |
| P-06 analepsis y narrador no fiable | `analepsis` por escena en la ficha; `destapa` permite la resurrección; la regla del POV no aplica a `narrador_no_fiable` ni a `multiple`; fuera el solape de escenas y el objeto sin paradero | `inicio` libre y `obj-004` en `humo-0003` | RF-07, RF-28 |
| P-07 nombres propios | Heurística de §8.3, como gate | 0 falsos positivos en 74 candidatos | RF-08 |
| P-08 léxico vetado | Gate, solo en `validar --final`; `lexico_vetado` aparte de `prohibiciones` | Las seis `prohibiciones` son descriptivas | RF-10 |
| P-09 umbrales de la huella | Señal, no gate; tolerancias de §8.5 | Frase media al 46 % de `ritmo`; Burrows 0,46–0,59 | RF-11, RF-12 |
| P-10 `k`, banda, carga, contexto | 3, 2, umbral estructural (0 antes del clímax o tres bajadas en el acto 2) y 70.000 | Desviaciones +1, 0, −1; carga 12, 9, 0; contexto máximo 46.676 | RF-14 a RF-16, RF-22 |
| P-11 última escena | Tras la última línea igual a `convenciones_formato.separador_escena`, `* * *` por defecto; se busca en el capítulo que vio el `lector-suspense` | En los tres capítulos, `* * *` separa exactamente las escenas del frontmatter | RF-17 |
| P-12 agente `sonda` | Rol nuevo; `Read, Write`; sonnet; moda de tres y mediana ≥ 0,5; cadencia de §8.1 | — | RF-04, RF-30 |
| P-13 marcas de compactación | `compact_boundary` más `isCompactSummary`, con `message.id` repetido en varias líneas | Compactación forzada el 2026-09-24 | RF-20, RF-22 |
| P-14 origen del modelo | `toolUseResult.resolvedModel` desde el transcript principal, al terminar la sesión | Las cuatro sesiones de capítulo de `humo-0003` | RF-13 |
| P-15 cuota sin tocar capítulos cerrados | Se suprimen los niveles 2 a 4; queda la parada limpia | — | RF-24 |
| P-16 `novela budget` | Fuera, a una spec propia | Sin datos de consumo por ventana | RF-23 |
| P-17 hilos y pistas fuera del plan | Igualdad | Los tres capítulos de `humo-0003` la cumplen | RF-09 |

### Cambios de la v0.3

Se acepta. Los requisitos provisionales de la v0.2 se concretan sin cambiar de id, salvo RF-23, que sale. Entran RF-25 a RF-30, que la v0.2 describía en §5 sin requisito (control negativo, calibración, canario del orquestador, campos de plan, código 5 y agente `sonda`). RF-13 registra el modelo en la trayectoria y no en `manifest.json`. RF-17 se comprueba en `novela gate`, no en `validar`, porque el `editor-estilo` reescribe la última escena después de que el `lector-suspense` la juzgue. RF-19 no escribe `estado.db`, y su cuenta se reinicia tras una intervención resuelta.

Antes de implementarla, el catálogo de `validators.md` §4.18 y el plan destaparon veinte huecos, que se cerraron en esta misma versión porque ningún requisito estaba hecho. Los más grandes: un gate `final` propio para el `editor-estilo`, separado del `mecanico`; la repetición del gate, que solo cuenta como tal sin otra orden en medio, para que un agente que no escribe nada no deje el bucle sin fin; una resolución que autoriza su causa; RF-01 filtra también `arco_previsto` y `rol_narrativo`; el solape exime lo ya permitido; las citas tienen un mínimo de 15 caracteres; la trayectoria usa `NOVELA_SESSION_ID` como clave y acepta `Agent`; y la receta del `cronista` gana `canon/mundo` y el reparto, sin los que los invariantes 3 y 4 habrían rechazado los tres deltas de `humo-0003`.
