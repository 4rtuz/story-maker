# Fase 4 — Los procedimientos

**Objetivo.** Que el orquestador tenga un procedimiento que seguir para crear, continuar y cerrar
una novela.

**Al terminar existe**: `.claude/commands/novela-nueva.md`, `novela-continuar.md` y
`novela-auditar.md`.

**Cierra**: RF-13 a RF-16, RF-29, RF-34. CA-18, CA-22 (revisión y un test cada uno) y CA-24
(revisión). El resto se acepta con CA-10, en la fase 7.

Requiere la fase 1 (los nombres de los agentes) y la 3 (sin el run de arranque, `/novela-nueva`
deja el capítulo 1 atribuido a un canon vacío).

**Es prosa, no código.** No hay TDD (`AGENTS.md`): la única verificación es la novela de humo
(`validators.md` §5.8). Lo que sí hay es una lista de revisión por fichero, al final de cada
tarea, contra los RF de la spec. Pásala antes de commitear.

---

## Orden y por qué

La plantilla del prompt de Task primero (4.1), porque la usan los otros dos procedimientos y es
lo que RF-15 acota. Después `/novela-nueva` (4.2), que es corto y deja un workspace con el que
leer `/novela-continuar` (4.3) en seco. `/novela-auditar` (4.4) es trivial.

---

## Forma común de los tres ficheros

```markdown
---
description: <una línea: qué hace y cuándo>
argument-hint: <slug> [--capitulos N]
---

<procedimiento numerado>
```

- **Sin `allowed-tools`** en el frontmatter. Los permisos viven en `settings.json` y en un solo
  sitio. Un `allowed-tools` aquí sería una segunda allowlist que CA-06 no vigila.
- Los argumentos llegan en `$ARGUMENTS`. El procedimiento empieza por separarlos y, si falta el
  slug, para con un mensaje de uso sin ejecutar nada.
- Cada paso nombra la orden exacta. El orquestador no deduce órdenes: las copia.
- **Códigos de salida del CLI**, iguales en los tres, que el procedimiento repite en una tabla
  corta porque decide sobre ellos:

  | Código | Qué hace el procedimiento |
  |---|---|
  | 0 | Sigue |
  | 1 | Gate fallido: reintento, según el paso |
  | 2 | Uso incorrecto: el procedimiento está mal. Para sin `intervencion.md` |
  | 3 | Lock ocupado: otro proceso trabaja en la novela. Para sin `intervencion.md` |
  | 4 | Workspace inválido: `intervencion.md` y para. No es un gate, no se reintenta. **Única excepción**: el briefing del `trazador` en `/novela-nueva` (4.2) |

- **Las tres reglas de lectura de la spec §5.4 (RF-29), literales en los dos procedimientos con
  gates**:
  1. **Un 1 solo es un gate si el log lo dice.** Tras un 1 de `validar` o `aplicar-delta`, lee la
     última línea de `harness.log`. Si contiene `<orden> NN -> 1`, es un gate. Si no la contiene
     (un traceback, un import roto, `-> error`), para sin reintentar y sin `intervencion.md`,
     porque ningún agente puede arreglar el CLI.
  2. **Un veredicto ilegible es un rechazo.** Si un `qa/` falta, no es JSON o no tiene `veredicto`,
     el gate lo trata como rechazo.
  3. **Una intervención se resuelve con una línea.** Un `intervencion.md` sin la línea
     `resuelto: <sha o motivo>` está vivo.

---

## 4.1 — Plantilla del prompt de Task (RF-15)

El prompt de cada Task es exactamente esto, y nada más:

```
slug: <slug>
capítulo: <NN>
briefing: novelas/<slug>/<ruta que imprimió novela briefing>
salidas: <rutas de §5.1 con NN sustituido, relativas a novelas/<slug>/>
reintento: <rutas de qa/ que lo motivan>        ← solo en reintento
causa: <una línea de harness.log>               ← solo en reintento del cronista o del arquitecto
```

- La ruta del briefing se toma de la **salida** de `novela briefing`
  (`runs/<run_id>/briefings/NN-<agente>.md · … tokens`), no se reconstruye. Así el orquestador no
  necesita saber qué run está abierto.
- Nunca prosa del orquestador, resúmenes, «ten cuidado con…», ni el capítulo. Si el orquestador
  cree que el agente necesita algo más, eso es un defecto de la receta y se arregla en
  `recipes.yaml`, no en el prompt (`CLAUDE.md`, «Permisos»).
- Seis líneas como máximo. RNF-02 permite 15; el resto es margen, no invitación.
- El retorno del agente se lee y no se re-inyecta en otro prompt.

La plantilla se escribe **en los dos procedimientos que la usan**, no en un fichero compartido:
un slash command no incluye otro, y el orquestador tiene que verla en el procedimiento que está
siguiendo.

---

## 4.2 — `/novela-nueva`

**Construye**: `.claude/commands/novela-nueva.md`.

`argument-hint: <slug> --idea "..." [--capitulos N] [--palabras P]`

Pasos, de la spec §5.4:

1. `novela nueva <slug> --idea "..." [--capitulos N] [--palabras P]`, con los flags tal como
   llegaron. Código distinto de 0 → para e informa.
2. `novela briefing <slug> 1 arquitecto` → Task `arquitecto`, con salidas
   `canon/{premisa,mundo,estilo,misterio}.md` y `canon/personajes/*.md`.
3. `novela briefing <slug> 1 trazador`. Este paso es también el **gate del `arquitecto`**: el
   briefing valida el canon contra sus modelos al cargarlo.
   - Sale con 0 → Task `trazador`, con salidas `plan/escaleta.md` y `plan/capitulos/NN.md` para
     todos los capítulos.
   - Sale con 4 **y** la última línea de `harness.log` del run de arranque contiene
     `briefing 01 trazador -> error · WorkspaceInvalido` → es el gate. Reintento del
     `arquitecto`, con `causa:` = lo que sigue a `·` en esa línea. Es la excepción a la tabla de
     códigos de la spec §5.4: `con_codigos` convierte `WorkspaceInvalido` en 4, no en 1.
   - **Cuenta de intentos**: las líneas `briefing 01 trazador -> error · WorkspaceInvalido` de ese
     log (la ruta del run sale del paso 2). Con dos reintentos agotados, `intervencion.md` en ese
     run y para.
   - Cualquier otro código, o un 4 sin esa línea → tabla de códigos.

   **Test que fija la línea** (CA-18), en `novela/slices/briefing/test_briefing.py::test_canon_invalido_en_el_log`:
   con un `canon/premisa.md` que no valida, `novela briefing <slug> 1 trazador` sale con 4 y la
   última línea de `harness.log` contiene esa subcadena. Es el único test de esta fase: el
   procedimiento depende de un formato de log, y si alguien lo cambia, que falle CI y no la
   primera novela. **Commit** aparte, antes que el procedimiento:
   `test(briefing): la línea de log del canon inválido es contrato de /novela-nueva`.
4. Devuelve: los ids creados (el retorno del `arquitecto`, tal cual, tres líneas) y la orden
   siguiente, `/novela-continuar <slug>`.

**Hueco que la spec no cubre, y cómo se trata**: nada valida el plan del `trazador` antes del
primer capítulo. El primer `novela briefing <slug> 1 escritor` carga la ficha y saldría con 4 si
es inválida. Con la tabla de códigos de arriba, eso es `intervencion.md` y parada: el `trazador`
es de arranque y `/novela-continuar` no lo reintenta. Si la novela de humo lo encuentra, la
solución es un paso 3b aquí que reintente al `trazador`, y va a la spec como enmienda, no se
improvisa en el procedimiento.

**Revisión** (RF-13, RF-29): los cuatro pasos en ese orden; el briefing del `trazador` antes de su
Task; el reintento es del `arquitecto`, no del `trazador`; la cuenta sale del log; la excepción
del 4 está escrita con su línea de log; la tabla de códigos y las tres reglas de lectura están.

**Commit**: `feat(comandos): /novela-nueva`

---

## 4.3 — `/novela-continuar`

**Construye**: `.claude/commands/novela-continuar.md`.

`argument-hint: <slug> [--capitulos N]`. Sin `--capitulos`, uno (D-7).

### Por capítulo

De la spec §5.4, con la decisión que falta en cada rama:

1. **Situación.**
   - `novela pendiente <slug>`: distinto de 0 → termina, «no quedan capítulos».
   - `novela estado <slug> --breve`.
   - Si existe algún `novelas/<slug>/runs/*/intervencion.md` **sin** una línea `resuelto:` → para
     y nombra el fichero (regla de lectura 3). Este paso va **antes** que cualquier `novela
     briefing`: el ensayo de CA-19 comprueba que la sesión para sin crear ningún run.
   - `NN` = capítulo de `checkpoints/latest.json` + 1, o `01` si no existe. El ancho de `NN` es el
     del workspace: lo da el propio `latest.json` o la salida de `novela briefing`.
   - Punto de reanudación: ver abajo.
2. `novela briefing <slug> <cap> escritor` → Task `escritor`, salida `capitulos/NN.md`.
3. `novela validar <slug> <cap>`. Sale con 1 → reintento del `escritor` con
   `reintento: qa/NN-validacion.json`, **con el mismo briefing** (no se regenera: el del escritor
   no incrusta el capítulo) y vuelta a 3.
4. **Los tres briefings de revisión, todos antes de lanzar ninguna revisión**: `continuista`,
   `editor-estilo`, `lector-suspense`. Después, **tres Task en un solo turno**. El orden importa
   por la custodia (0001 RF-32): los tres tienen que incrustar el mismo hash del capítulo, y el
   `editor-estilo` lo cambia.
5. `novela validar` otra vez, porque el `editor-estilo` ha reescrito el capítulo. Sale con 1 →
   reintento del **`editor-estilo`** con su **mismo briefing** y `reintento: qa/NN-validacion.json`,
   y se repite 5. Regenerar su briefing rompería la custodia (P-07).
6. **Gate de revisión**: lee el campo `veredicto` de `qa/NN-continuidad.json` y
   `qa/NN-suspense.json`, y **solo ese campo**. Si alguno rechaza, o no se puede leer (regla de
   lectura 2) → reintento del `escritor` con `reintento:` esas dos rutas, y vuelta a 3.
7. `novela briefing <slug> <cap> cronista` → Task `cronista`, salida `estado/deltas/NN.json` →
   `novela aplicar-delta <slug> <cap>`. Sale con 1 y la última línea contiene
   `aplicar-delta NN -> 1` → reintento del `cronista` con `causa:` = lo que sigue a `·`, y vuelta a
   `aplicar-delta`. **Salvo si esa causa empieza por `custodia:`**: lo roto es el orden o el
   capítulo, no el delta, y el `cronista` no puede arreglarlo. `intervencion.md` y para.
8. `novela checkpoint <slug> <cap>`.

### Cuenta de intentos

Antes de **cada** reintento, lee `runs/<run_id>/harness.log` (el `run_id` sale de la ruta del
briefing del paso 2) y cuenta:

| Gate | Líneas | Consumidos |
|---|---|---|
| Mecánico (pasos 3 y 5) | `validar NN -> 1` | todas |
| Revisión (paso 6) | `briefing NN continuista -> 0` | todas menos una |
| Delta (paso 7) | `aplicar-delta NN -> 1` | todas |

Con 2 consumidos, el siguiente fallo no reintenta: escribe `runs/<run_id>/intervencion.md` con el
gate, los intentos, y las rutas de `qa/` y del último briefing, y para. La plantilla, literal en
el procedimiento:

```markdown
# Intervención — capítulo NN

gate: mecánico | revisión | delta
intentos: 3
briefing: runs/<run_id>/briefings/NN-<agente>.md
qa: qa/NN-validacion.json, …
```

El fichero lo escribe el orquestador con `Write`: `runs/` está dentro de `novelas/**`, que el
`allow` autoriza, y la sesión principal solo tiene la regla 1 del hook.

**Nunca cuentes en la conversación** (invariante 5). Se compacta y no sobrevive a una
reanudación.

### Punto de reanudación (D-8)

RNF-04 pide que un corte se reanude «repitiendo el primer paso no confirmado». Tres marcas de
disco, comprobadas en este orden sobre el run abierto del capítulo `NN`:

| Si… | Reanuda en |
|---|---|
| `harness.log` tiene `aplicar-delta NN -> 0` | paso 8 |
| existe `estado/deltas/NN.json` y el log tiene `briefing NN cronista -> 0` | `aplicar-delta` del paso 7 |
| existe `capitulos/NN.md` y la última línea `validar NN` del log es `-> 0`, sin ningún `briefing NN continuista` después | paso 4 |
| cualquier otro caso | paso 2 |

El run abierto se localiza sin reconstruirlo: `runs/*/manifest.json` con `capitulo: NN` y
`fase: "capitulo"`, el más reciente. Si no hay ninguno, paso 2.

**Techo conocido**: si el corte cae a mitad de las revisiones, se reanuda en 2 o en 4 y los
briefings de revisión se regeneran, lo que suma una línea `briefing NN continuista -> 0`. Un
corte a mitad de revisión consume así un intento del gate de revisión. La cuenta nunca se reinicia
(que es lo que protege RNF-04); como mucho, se consume de más. `novela gate` de la 0002 lo
resuelve con código.

**Revisión** (RF-14, RF-29): las tres reglas de lectura y la tabla de códigos; `custodia:` va a
intervención; briefings de revisión antes de ninguna revisión; `validar` después del
editor y reintento al editor sin regenerar; `cronista` después del gate; la cuenta desde
`harness.log`; `intervencion.md` al tercer fallo; ningún paso lee `capitulos/NN.md` (`CLAUDE.md`:
el orquestador no lee prosa); todos los prompts de Task según 4.1.

**Commit**: `feat(comandos): /novela-continuar con cuenta de intentos en harness.log`

---

## 4.4 — `/novela-auditar`

**Construye**: `.claude/commands/novela-auditar.md`.

1. `novela auditar <slug>`.
2. Sale con 0 → `novela exportar <slug> --formato md` y `novela exportar <slug> --formato epub`,
   e informa de las dos rutas.
3. Sale con 1 → informa de los hallazgos (la salida del comando, tal cual) y **no exporta**.

**Revisión** (RF-16): no exporta con hallazgos.

**Commit**: con 4.3, o `feat(comandos): /novela-auditar`.

---

## 4.5 — Docs de referencia

En el commit de la última tarea de la fase:

- `CLAUDE.md`, «Bucle por capítulo»: el bloque resumido gana el segundo `novela validar` después
  de las revisiones y pone el `cronista` después del gate. Sustituye el bloque; no crece más de
  dos líneas.
- `architecture.md` §3.1: `commands/` en el árbol.

---

## 4.6 — Enmienda v0.4: F-09 y la fila del 1

**Estado de partida**: las tareas 4.1 a 4.5 están hechas. La tabla de códigos de los dos
procedimientos ya dice que un 1 de `briefing` (y en `novela-continuar.md`, de `checkpoint`) no se
reintenta. La v0.4 solo lo sube a la spec.

1. **Test primero** (CA-22), en `novela/slices/briefing/test_briefing.py::test_misterio_invalido_en_el_log`:
   con un canon válido salvo `canon/misterio.md`, `novela briefing <slug> 1 trazador` sale con 4, y
   la última línea de `harness.log` contiene `WorkspaceInvalido` y `misterio.md`. Se ve en rojo
   antes de dar nada por bueno. Si sale verde a la primera, porque `WorkspaceInvalido(f"{ruta}: …")`
   ya pone la ruta, se rompe a propósito el formato de la causa para verlo fallar, y se restaura.
   Si `misterio.md` no se valida al cargar el canon, el test lo destapa: para, y se anota en la
   spec antes de seguir.

   **Commit**: `test(briefing): la causa de un misterio inválido nombra el fichero`
2. **`novela-nueva.md`, paso 3**: un punto tras la cuenta de intentos. Si la causa contiene
   `misterio.md`, no hay reintento: `intervencion.md` en el run de arranque, con gate `arquitecto`
   y la causa, y se para. Se busca `misterio.md` sin separador, porque en Windows la ruta va con `\`.
   Una línea de motivo: el `arquitecto` no puede leer ese fichero, así que tampoco sobrescribirlo.
3. **El cuerpo del `arquitecto`** sigue mandando fallar citando la causa si le toca reescribir un
   fichero que no puede leer. No se toca: con la v0.4 ese caso ya no le llega, y si llegara, falla
   bien.
4. **Revisión** (CA-22, CA-24):
   - la excepción de F-09 está en el paso 3, **antes** del reintento;
   - la tabla de códigos de `novela-nueva.md` nombra el 1 de `briefing`;
   - la de `novela-continuar.md` nombra el 1 de `briefing` y el de `checkpoint`.

**Docs**, en el commit del paso 2: `validators.md` §4.17, F-09 pasa a `activo (CA-22)`.

**Cierra**: RF-34, RF-29 en lo que añade la v0.4. CA-22, CA-24.

**Commit**: `feat(comandos): /novela-nueva no reintenta un misterio inválido (F-09)`

---

## Al terminar la fase

- Lectura en seco: sobre un workspace de la fábrica (`uv run pytest` deja los de `conftest` en
  `tmp_path`; o `novela nueva prueba …` a mano), recorre `/novela-continuar` con el dedo, orden a
  orden, sin lanzar modelo. Cada orden existe, con los argumentos que el CLI acepta.
- No hay filas de trazabilidad todavía: RF-13 a RF-16 se aceptan con CA-10 en la fase 7. Las de
  CA-22 y CA-24 sí: pasan a `hecho` con la tarea 4.6.
