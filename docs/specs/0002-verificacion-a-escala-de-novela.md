---
spec: 0002
titulo: "Verificación a escala de novela: secreto, estado, estilo, tensión y orquestador"
estado: borrador
autor: ""
fecha: 2026-09-23
version: 0.2
afecta: [backend, agentes, esquemas, docs]
depende_de: [0001, 0003]
sustituye: []
adr: []
commit: null
---

# 0002 — Verificación a escala de novela: secreto, estado, estilo, tensión y orquestador

## 1. Propósito y alcance

Cerrar los cinco modos de fallo que `docs/validators.md` describe y que ningún gate actual detecta: misterio roto, contaminación del estado, deriva de estilo, colapso de la tensión y degradación silenciosa de la sesión orquestadora. Es para el orquestador, que hoy los descubriría tarde, y para quien lea la novela.

La spec 0001 v0.3 ya fija la **forma** que esto necesita: custodia por hash, sello de capítulos cerrados, `cita` opcional en las colecciones append-only y fichas de personaje estructuradas (0001 §5.6). Esta spec es la **política** que usa esos campos, más todo lo que no cabía en la 0001 porque abría una pregunta.

**Dentro del alcance**

- Secreto: filtrado por campo de la ficha de personaje, solape con lo no revelado, QA saneado para el reintento, sondas ciegas, pistas y pistas falsas con cita.
- Estado: cita obligatoria, invariantes narrativas del delta, resúmenes acotados, cruce con el plan.
- Estilo: léxico vetado, huella estilométrica, origen del score `estilo`, modelo resuelto por agente.
- Tensión: `novela validar-plan` con la forma de la curva, carga de preguntas abiertas, banda y tendencia, gancho con cita, calibración del juez.
- Orquestador: `novela gate`, auditoría de trayectoria, freno en `pendiente`, contexto medido, degradación registrada, canario.

**Fuera del alcance**

- Lo que ya está en la 0001 v0.3 (RF-30 a RF-36).
- La contención de `architecture.md` §12.7: agentes, hooks, permisos, la regla `deny` sobre `canon/misterio.md` y el canario de las barreras. Es la spec 0003, de la que esta depende. También es de la 0003 la procedencia de `.claude/` en `manifest.json` (`sucio` y hashes de agentes y comandos). Aquí queda solo el modelo resuelto por invocación (RF-13).
- El índice recuperable (`architecture.md` §12.4).
- Los prompts concretos de los agentes. Esta spec fija contratos de entrada y salida; el texto de los prompts se valida por novela de humo (`AGENTS.md`).

## 2. Problema

Cada capítulo puede pasar todos sus gates mientras la novela falla en conjunto. La evidencia es documental: el backend de la 0001 está implementado, pero no hay ninguna ejecución real hasta que la 0003 construya `.claude/`. Las referencias son a `docs/validators.md`, donde está el análisis completo.

- **El secreto viaja parafraseado.** El guardarraíl de RF-09 busca texto literal de `misterio.md`. Llegan al `escritor` sin pasar por él: las fichas del `trazador`, que conoce la solución; la ficha del culpable, cuyo `secreto` es la solución; y el `qa/` del reintento, escrito por revisores que la ven (`validators.md` §4.9).
- **El `cronista` escribe en tablas que no admiten corrección** y solo `libro_de_hechos` exige evidencia. Nada comprueba que un muerto no reaparezca, ni que un resumen no invente un personaje (§3.9.8, §3.9.11).
- **La deriva de estilo se ancla en el capítulo anterior**, no en el canon, y el `editor-estilo` se puntúa a sí mismo (§4.2, §4.13).
- **El gate de tensión no tiene banda**, el juez tiende a saturarse en alto y el `lector-suspense` juzga la previsibilidad conociendo la solución (§4.2, §4.13).
- **El orden del bucle solo está escrito en prosa**, la sesión decide los gates y la cuenta de intentos vive en su memoria, que se compacta (§4.16, §5.8, §5.11).

## 3. Actores y partes implicadas

| Actor | Interés en este cambio |
|---|---|
| Orquestador | Deja de decidir los gates si se acepta `novela gate` (P-02); gana la auditoría de su trayectoria y un freno en `pendiente` |
| Agente `escritor` | Recibe un briefing y un reintento filtrados; su frontmatter gana citas de pistas |
| Agente `cronista` | La cita deja de ser opcional; sus deltas pasan por las invariantes narrativas |
| Agentes `continuista`, `lector-suspense` | Su QA se sanea antes de llegar al escritor; el `lector-suspense` devuelve el gancho con cita y deja de puntuar la previsibilidad |
| Agente `editor-estilo` | Su score lo calcula el CLI, no él |
| Agente `arquitecto` | Enlaza cada revelación con los secretos que destapa (P-04) |
| Agente nuevo `sonda` | Responde quién es el culpable sin conocer el misterio (P-12) |
| Operador humano | Revisa las paradas por trayectoria, sello, compactación o cambio de modelo |

## 4. Contexto y restricciones

- **Invariantes que aplican**: el **3** (el secreto), el **4** (fair play), el **5** (contexto en disco: la trayectoria se escribe en `runs/`), el **7** (la degradación por cuota de `architecture.md` §9 lo viola en sus niveles 2 y 4, y el sello de 0001 RF-35 ya lo detecta) y el **1** (ninguna verificación nueva escribe `estado.db`).
- **Restricciones técnicas**: el CLI no llama a modelos (0001 RNF-03). Las sondas ciegas y la calibración del juez son invocaciones de agente por `Task` desde el orquestador; el CLI solo compara sus salidas contra el canon.
- **Supuestos**: (a) el transcript de Claude Code marca las compactaciones (P-13). La otra mitad del supuesto ya está verificada: el experimento de la 0003 (`docs/implementation-plans/0003-contencion/decisiones-abiertas.md`, E-5) muestra que cada subagente tiene su transcript aparte, en `<sesión>/subagents/agent-<id>.jsonl` y con `isSidechain: true`, que el hook `SubagentStop` entrega su ruta y que cada mensaje de asistente lleva `message.model`; (b) una novela de humo de tres capítulos basta para dar un primer valor a los umbrales, que se revisan con la primera novela completa.
- **Dependencias**: la 0001 v0.3 implementada y la 0003, que construye los agentes, los hooks y la novela de humo de la que salen P-09, P-10 y P-13. `novela gate` necesita además un ADR (P-02).

## 5. Propuesta

Cinco bloques, uno por fallo. Cada punto remite a la sección de `validators.md` que lo motiva, y a la pregunta de §16 que lo bloquea si la hay.

### 5.1 Misterio roto

1. **Filtro por campo** (`validators.md` §4.4). `novela briefing` excluye `secreto` y `coartada_y_cronologia_privada` de las fichas que recibe el `escritor` o el `editor-estilo`, salvo que una revelación con `capitulo_previsto ≤ N` las autorice. Bloqueado por P-04: hoy ninguna revelación apunta a un secreto, y no todos los secretos son del misterio central.
2. **Solape con lo no revelado** (§3.9.1, §4.4). `novela briefing` aborta si el briefing del `escritor` o del `editor-estilo` comparte bloques de cinco palabras con `verdad_oculta` o con una revelación de `capitulo_previsto > N`. `novela validar-plan` aplica la misma comprobación a cada ficha de capítulo. Sin preguntas: el tamaño del bloque es un parámetro con valor por defecto 5.
3. **QA saneado para el reintento** (§4.4). Del `qa/` solo entran en el briefing del reintento campos de una lista blanca, y se descartan los hallazgos que citan `rev-`, `pfa-` o al culpable. Bloqueado por P-05.
4. **Sondas ciegas** (§4.15). Un agente `sonda` sin herramientas recibe solo el briefing del `escritor` (sonda del briefing) o los capítulos del acto (sonda del texto), y escribe `qa/NN-sonda.json` con `{culpable_id, confianza}`. Se vota tres veces. `novela` compara la moda con `culpable_o_amenaza` y con el `capitulo_previsto` de la revelación que lo destapa. Bloqueado por P-12.
5. **Pistas y pistas falsas con cita** (§3.9.4, §3.9.10). En el frontmatter, `pistas_plantadas` y `pistas_pagadas` pasan a ser listas de `{id, cita}`, y aparece `pistas_falsas_desmontadas: [{id, cita}]`. `validar` exige que cada cita sea subcadena del cuerpo, con la normalización de 0001 RF-33. Sin preguntas propias; cambia el contrato de salida del `escritor`.

### 5.2 Contaminación del estado

1. **Cita obligatoria** (§3.9.8) en `conocimiento`, `linea_temporal` y `conocimiento_lector`, sobre el campo que la 0001 ya creó como opcional. Bloqueado por P-03.
2. **Invariantes narrativas en `aplicar-delta`** (§3.9.8), property-based: un personaje muerto no reaparece ni aprende nada; toda `ubicacion` es un escenario del canon; solo se cierra un hilo abierto y solo se paga una pista plantada; nadie está en dos escenas solapadas; un objeto de relevancia alta no queda sin poseedor ni ubicación; con POV limitado, `conocimiento_lector` incluye lo que aprende el personaje POV en el capítulo. Bloqueado por P-06.
3. **Resúmenes acotados** (§3.9.11). Todo id y todo nombre propio de `memoria/resumenes/NN.md` aparece en el delta o en el cuerpo del capítulo. Bloqueado por P-07.
4. **Cruce con el plan** (§3.9.8). Hilos y pistas del frontmatter contra la ficha del capítulo. Bloqueado por P-17.

### 5.3 Deriva de estilo

1. **Léxico vetado** en `validar` (§3.9.9). Bloqueado por P-08.
2. **Huella estilométrica** en `validar` (§3.9.9, §4.13): longitud media y dispersión de frase, proporción de diálogo y Delta de Burrows sobre palabras funcionales, contra `parrafos_canonicos` y la media de los capítulos 1–3, nunca contra N-1. Las tolerancias van en `canon/estilo.md` `ritmo`. Bloqueado por P-09.
3. **Origen del score `estilo`** (§4.2): lo calcula el CLI desde la huella, no se toma de `qa/NN-estilo.json`. Depende de 5.3.2.
4. **Modelo resuelto por agente** (§4.13). `manifest.json` registra el id de modelo real de cada invocación; `pendiente` para si cambia entre dos capítulos. Bloqueado por P-14.
5. **Control negativo del editor** (§4.11): un fixture con léxico vetado y frases fuera de `ritmo`, con su tasa de detección por release. Sin preguntas; llama a modelo, así que no entra en `pytest`.

### 5.4 Colapso de la tensión

1. **`novela validar-plan <slug>`** (§3.9.1). Subcomando nuevo que corre una vez, tras el `trazador`. Comprueba el fair play del plan, los ids, el orden de las pistas y el solape de 5.1.2. Comprueba además la forma de `curva_tension_objetivo`: el clímax es su máximo, el punto medio es un pico local y no hay más de `k` capítulos seguidos sin subir en los actos 2 y 3. El valor de `k` queda bloqueado por P-10.
2. **Carga de preguntas abiertas** en cada `checkpoint` (§4.13): hilos abiertos + pistas plantadas sin pagar + revelaciones pendientes, desde `estado.db`. Umbrales bloqueados por P-10.
3. **Banda y tendencia** (§4.13): con `|tension_real − objetivo| > banda_tension` de `config.yaml` se reintenta; con desviación negativa tres capítulos seguidos se va a intervención. Valor bloqueado por P-10.
4. **Gancho con cita** (§3.9.10): el `lector-suspense` devuelve `gancho: {tipo, cita}`; la cita es subcadena de la última escena y el tipo es el `gancho_final` de la ficha. Bloqueado por P-11.
5. **Previsibilidad**: la da la sonda del texto (5.1.4), no el `lector-suspense`.
6. **Huecos de `tension_real`** (§4.13): la auditoría de acto los marca y no los interpola. Sin preguntas.
7. **Calibración del juez** (§4.11): capítulos fixture de tensión conocida por release. Si el plano recibe 6 o más, o la separación es menor que `banda_tension`, los scores del `lector-suspense` no valen como gate. Depende de P-10.

### 5.5 Degradación silenciosa del orquestador

1. **`novela gate <slug> <cap>`** (§4.4, §4.16). Lee `qa/*.json` y el cursor, sale con 0 para avanzar, 1 para reintentar o 2 para intervenir, e incrementa `cursor.intento` en `estado.db`. Se niega a un cuarto intento. Revierte la primera alternativa descartada de la 0001 (§15) y `architecture.md` §2.1: bloqueado por P-02.
2. **Auditoría de trayectoria** (§4.16). Un script determinista sobre el transcript, disparado por el hook `Stop`, escribe `runs/<run_id>/trayectoria-NN.json`. Comprueba el orden contra §4.10 y lo que no deja artefacto: lecturas de `capitulos/` desde la sesión principal, escrituras suyas en el workspace, `Task` a roles desconocidos, prompts de `Task` con prosa, retornos largos y agentes omitidos sin nivel registrado. Bloqueado por P-13.
3. **Freno en `pendiente`** (§4.4): código propio si falta la trayectoria del último capítulo o tiene violaciones. Depende de 5.5.2.
4. **Contexto medido** (§4.16): tokens por turno y compactaciones, desde el mismo transcript, con alerta por umbral y el capítulo marcado si hubo compactación a mitad. Depende de P-13 y de P-10.
5. **Degradación registrada** (§4.4): el nivel de cuota lo fija el CLI y queda en el manifiesto. Requiere `novela budget`, que la 0001 excluyó: bloqueado por P-16.
6. **Canario del orquestador** (§4.16), en la novela de humo. Depende de 5.5.1 y 5.5.2.

### 5.6 Degradación por cuota contra el invariante 7

El sello de 0001 RF-35 hace que los niveles 2 y 4 de `architecture.md` §9 paren el bucle, porque el `editor-estilo` diferido reescribe capítulos cerrados. La política de cuota tiene que degradar sin tocar un capítulo cerrado. Bloqueado por P-15.

## 6. Requisitos funcionales

Provisionales: cada uno se concreta al cerrar la pregunta que indica. Los que no remiten a ninguna están listos para aceptarse.

| Id | Requisito | Prioridad | Bloqueado por |
|---|---|---|---|
| RF-01 | `novela briefing` excluye `secreto` y `coartada_y_cronologia_privada` de las fichas del `escritor` y el `editor-estilo`, salvo revelación autorizada con `capitulo_previsto ≤ N` | debe | P-04 |
| RF-02 | `novela briefing` aborta sin escribir si el briefing del `escritor` o el `editor-estilo` comparte un bloque de 5 palabras con `verdad_oculta` o con una revelación de `capitulo_previsto > N` | debe | — |
| RF-03 | El briefing de reintento del `escritor` incluye del `qa/` solo los campos de la lista blanca y omite los hallazgos descartados por el criterio de P-05 | debe | P-05 |
| RF-04 | `novela` compara `qa/NN-sonda.json` con `culpable_o_amenaza` y marca fuga si la moda de tres votos acierta antes del `capitulo_previsto` | debe | P-12 |
| RF-05 | `validar` exige que cada pista plantada, pagada o falsa desmontada del frontmatter lleve una `cita` que sea subcadena del cuerpo | debe | — |
| RF-06 | `aplicar-delta` rechaza un delta sin `cita` en `conocimiento`, `linea_temporal` o `conocimiento_lector`, salvo lo que P-03 exima | debe | P-03 |
| RF-07 | `aplicar-delta` rechaza un delta que viola cualquiera de las invariantes narrativas de §5.2.2 | debe | P-06 |
| RF-08 | `aplicar-delta` rechaza un resumen con un id o un nombre propio ausente del delta y del cuerpo | debería | P-07 |
| RF-09 | `validar` contrasta hilos y pistas del frontmatter con la ficha del plan según P-17 | debe | P-17 |
| RF-10 | `validar` detecta las `prohibiciones` literales en el cuerpo | debe | P-08 |
| RF-11 | `validar` calcula la huella estilométrica y la compara con las tolerancias de `ritmo` | debería | P-09 |
| RF-12 | `checkpoint` emite el score `estilo` desde la huella de RF-11 | debería | P-09 |
| RF-13 | `manifest.json` registra el modelo resuelto de cada invocación; `pendiente` sale con su código propio si cambia entre capítulos | debería | P-14 |
| RF-14 | `novela validar-plan <slug>` comprueba fair play, ids, orden de pistas, solape de RF-02 sobre cada ficha y forma de la curva | debe | P-10 |
| RF-15 | `checkpoint` calcula la carga de preguntas abiertas y la registra; por debajo del umbral, emite alerta | debería | P-10 |
| RF-16 | El gate de tensión reintenta fuera de `banda_tension` e interviene con tres desviaciones negativas seguidas | debe | P-10 |
| RF-17 | `validar` exige que el `gancho.cita` del `lector-suspense` sea subcadena de la última escena y que `gancho.tipo` sea el `gancho_final` de la ficha | debería | P-11 |
| RF-18 | La auditoría de acto marca los capítulos sin `tension_real` y no los interpola | debe | — |
| RF-19 | `novela gate <slug> <cap>` sale con 0, 1 o 2 desde `qa/*.json` y el cursor, e incrementa `cursor.intento` | debe | P-02 |
| RF-20 | El hook `Stop` escribe `runs/<run_id>/trayectoria-NN.json` con las comprobaciones de §5.5.2 | debe | P-13 |
| RF-21 | `pendiente` sale con su código propio si falta la trayectoria del último capítulo o tiene violaciones | debe | P-13 |
| RF-22 | La trayectoria registra tokens por turno y compactaciones, y marca el capítulo si hubo compactación a mitad | debería | P-13 |
| RF-23 | El nivel de degradación lo fija `novela budget` y queda en `manifest.json` | debería | P-16 |
| RF-24 | La política de cuota no modifica ningún capítulo cerrado | debe | P-15 |

## 7. Requisitos no funcionales

| Id | Categoría | Requisito y umbral medible |
|---|---|---|
| RNF-01 | Rendimiento | `validar` sigue por debajo de 2 s para 4.000 palabras con la huella y el léxico vetado; `validar-plan` en < 5 s para 24 fichas |
| RNF-02 | Consumo de contexto | El QA saneado no hace crecer el briefing de reintento; la trayectoria no entra en ningún briefing |
| RNF-03 | Coste / cuota | Cero llamadas a modelo desde el CLI. Las sondas añaden 3 llamadas baratas en el primer capítulo de cada acto y en los capítulos que pagan pista, y 3 por frontera de acto |
| RNF-05 | Observabilidad | La trayectoria, la carga de preguntas abiertas y la huella llegan a Langfuse como scores del capítulo |
| RNF-06 | Compatibilidad | Hoy no hay novelas empezadas. Si las hubiera al aceptar esta spec, ver P-03 |

## 8. Interfaces y contratos

- **CLI**: **nuevos** `novela validar-plan <slug>` y `novela gate <slug> <cap>` (P-02). `pendiente` gana un código de salida propio para la trayectoria y el cambio de modelo, el mismo que `validators.md` §4.4 ya reserva para `intervencion.md`.
- **Esquemas**: frontmatter de capítulo con pistas `{id, cita}` y `pistas_falsas_desmontadas` (**ruptura** respecto a 0001, sin datos que migrar); `qa-informe.schema.json` gana `gancho`; nuevo `trayectoria.schema.json`; `config.schema.json` gana `banda_tension`; `canon.schema.json` gana el enlace entre revelación y secreto (P-04) y el tipo de las `prohibiciones` (P-08).
- **Contrato de agente**: **nuevo** agente `sonda`, sin herramientas, modelo según P-12. **Compatibles**: `escritor` (citas de pistas), `lector-suspense` (gancho, sin previsibilidad), `cronista` (cita obligatoria), `arquitecto` (enlace revelación–secreto).
- **Hooks**: un hook `Stop` propio, registrado en el `.claude/settings.json` de la 0003, ejecuta la auditoría de trayectoria. El envío de trazas no es suyo: lo hace el plugin de Langfuse con sus propios hooks `Stop` y `SessionEnd` (0003 §5.5).

## 9. Datos y estado

| Rama | Cambio |
|---|---|
| `canon/` | Enlace revelación–secreto y tipo de `prohibiciones`; tolerancias numéricas en `ritmo` |
| `plan/` | Sin cambios de forma; `validar-plan` lo lee |
| `estado/estado.db` | `cita` pasa a obligatoria (P-03); `cursor.intento` lo escribe `novela gate` (P-02) |
| `memoria/` | Sin cambios de forma; `aplicar-delta` valida los resúmenes contra el capítulo |

## 10. Migración y compatibilidad

No aplica mientras no haya novelas empezadas. Hay una ruptura: el frontmatter de pistas con cita. Si se acepta con alguna novela a medias, P-03 decide qué pasa con los capítulos sin cita.

## 11. Criterios de aceptación

Solo para los requisitos que no dependen de ninguna pregunta. El resto se escribe al cerrarla.

- [ ] **CA-02** (RF-02) property-based: un briefing del `escritor` con un bloque de 5 palabras de `verdad_oculta` o de una revelación futura hace salir a `briefing` con != 0 sin escribir el fichero; un briefing sin solape se escribe
- [ ] **CA-05** (RF-05) property-based: una pista del frontmatter sin cita, o con una cita que no es subcadena del cuerpo, nunca pasa `validar`
- [ ] **CA-18** (RF-18) sobre un fixture con un hueco en `tension_real`, la auditoría de acto lo reporta como hueco y no devuelve valor para ese capítulo

## 12. Trazabilidad

Se rellena durante la implementación.

## 13. Verificación

- **Property-based** en todo lo que toque `gates.py` o `delta.py`: RF-02, RF-05, RF-06, RF-07, RF-08, RF-10, RF-17 (`validators.md` §3.6).
- **Mutación** sobre las comparaciones de umbral de RF-11, RF-15 y RF-16.
- **Model checking** (§4.10) ampliado con `novela gate`: la enumeración pasa a ejercitar código, no solo la máquina ideal.
- **Novela de humo**: calibra los umbrales de P-09 y P-10 y ejecuta el canario del orquestador. Es la única verificación de las sondas y de la auditoría de trayectoria antes de una novela real.
- **Riesgos aceptados**: `validators.md` §5.12 (las sondas son de la misma familia de modelo) y §5.13 (las invariantes narrativas cubren lo que se puede escribir como regla).

## 14. Impacto

| Área | Cambio |
|---|---|
| Invariantes | Ninguno se toca. El 3 gana medida directa (sondas); el 7 deja de chocar con la política de cuota (RF-24) |
| Esquemas | Los de §8; hay que regenerar `backend/schemas/` y actualizar `definitions.md` en el commit de cada uno |
| Contratos de agente | Un agente nuevo (`sonda`) y cuatro contratos de salida modificados (§8) |
| Docs de referencia | `architecture.md` §2.1 si se acepta P-02 (quién decide los gates), §7.2 (frontmatter), §7.4 y §7.5 (agente `sonda`), §9 (niveles 2 y 4); `validators.md` pasa de «v1» a estado real en cada método que se implemente |
| ADR | Uno si se acepta `novela gate` (P-02) |
| Frontend | La trayectoria y la carga de preguntas abiertas son candidatas al panel de progreso; fuera de esta spec |

## 15. Alternativas descartadas

- **Meterlo todo en la 0001.** La 0001 está aceptada y no admite preguntas abiertas (`_plantilla.md` §16). Solo entró lo que se podía cerrar en el propio texto.
- **Detectar la paráfrasis del secreto con embeddings.** Añade una dependencia de modelo local para algo que la sonda mide directamente: si con el briefing se puede deducir el culpable, no importa por qué vía.
- **Que el `lector-suspense` juzgue la previsibilidad.** Conoce la solución; no puede medir una incertidumbre que no tiene.
- **Comparar el estilo de cada capítulo con el anterior.** Una deriva gradual pasa cualquier comparación entre vecinos.

## 16. Preguntas abiertas

- [ ] **P-01** ¿Una spec o varias? Mezcla cinco cambios y tres superficies: CLI, `.claude/` y agentes. Partición propuesta: CLI mecánico (5.1.2, 5.1.5, 5.2, 5.3.1–5.3.3, 5.4.1–5.4.4, 5.4.6), orquestador (5.5, con su ADR), agentes y sondas (5.1.1, 5.1.3, 5.1.4, 5.3.5, 5.4.7) y política de cuota (5.5.5, 5.6) — autor
- [ ] **P-02** ¿Se mueve el juicio de los gates de la sesión al CLI con `novela gate`? Revierte 0001 §15 y `architecture.md` §2.1; si sí, ADR — autor
- [ ] **P-03** ¿La cita es obligatoria cuando el conocimiento es inferido o el tiempo es implícito («dos horas después»)? Opciones: obligatoria siempre, u opcional con `inferido: true` y hallazgo de gravedad baja — autor
- [ ] **P-04** ¿Qué secretos se filtran al `escritor`, y cómo enlaza una revelación con el `secreto` que destapa? No todos los secretos son del misterio central (`definitions.md` §2.3) — autor
- [ ] **P-05** ¿Con qué criterio se descarta un hallazgo del QA que menciona al culpable, que aparece de forma legítima en muchos? ¿Se pierde `correccion_sugerida` entera? — autor
- [ ] **P-06** ¿Cómo se representan la analepsis y el narrador no fiable? Un muerto reaparece en un flashback, el flashback solapa escenas en `linea_temporal`, y el narrador no fiable rompe la regla del POV — autor
- [ ] **P-07** ¿Qué heurística identifica un nombre propio en un resumen en español, y con qué tasa de falsos positivos es aceptable? — autor, con la novela de humo
- [ ] **P-08** ¿El léxico vetado es gate o señal? ¿En la primera `validar` o solo en la posterior al editor? ¿Las `prohibiciones` se tipan en `literal` y `descriptiva`? — autor
- [ ] **P-09** Umbrales de la huella estilométrica — novela de humo
- [ ] **P-10** Valores de `k`, `banda_tension`, el umbral de carga de preguntas abiertas y el de contexto — novela de humo
- [ ] **P-11** ¿Dónde empieza la última escena? Depende del separador de `convenciones_formato`, que hoy no está fijado — autor
- [ ] **P-12** Agente `sonda`: ¿rol nuevo o variante de uno existente? ¿Qué modelo? ¿Qué umbral de `confianza` cuenta como acierto? ¿Cadencia final? — autor
- [ ] **P-13** ¿El transcript marca las compactaciones, y cómo? Requiere una prueba que fuerce una compactación en la versión actual de Claude Code. Dos partes de la pregunta original ya están cerradas:
  - La distinción entre sesión principal y subagente la resolvió la 0003 (E-5): hay un fichero por subagente, con `isSidechain: true`, y la ruta llega en `SubagentStop`.
  - La auditoría vive en esta spec, y la 0003 construye los hooks de los que depende.

  — autor, tras la prueba
- [ ] **P-14** ¿De dónde sale el id de modelo resuelto? La 0003 (E-5) observó `message.model` con el id completo en cada mensaje de asistente, tanto en el transcript principal como en el de cada subagente. Queda decidir si se lee de ahí al cerrar la sesión o por invocación desde `SubagentStop` — autor
- [ ] **P-15** ¿Cómo degrada la política de cuota sin tocar capítulos cerrados? Opciones: el editor en lote antes del `cronista` de cada capítulo del lote, o suprimir los niveles 2 y 4 — autor
- [ ] **P-16** ¿`novela budget` entra en esta spec? La 0001 lo aplazó por falta de datos de calibración — autor
- [ ] **P-17** ¿Puede el `escritor` abrir un hilo o plantar una pista fuera del plan? Decide si el cruce con el plan exige igualdad o inclusión — autor
