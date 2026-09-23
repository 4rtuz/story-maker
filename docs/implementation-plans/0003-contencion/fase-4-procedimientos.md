# Fase 4 — Los procedimientos

**Objetivo.** Que el orquestador tenga un procedimiento que seguir para crear, continuar y cerrar
una novela.

**Al terminar existe**: `.claude/commands/novela-nueva.md`, `novela-continuar.md` y
`novela-auditar.md`.

**Cierra**: RF-13 a RF-16. Se aceptan con CA-10, en la fase 7.

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
  | 4 | Workspace inválido: `intervencion.md` y para. No es un gate, no se reintenta |

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
   - Sale con distinto de 0 → reintento del `arquitecto`, con `causa:` = el stderr del briefing.
     **Cuenta de intentos**: las líneas `briefing 01 trazador -> ` con código distinto de 0 del
     `harness.log` del run de arranque (la ruta sale del paso 2). Con dos reintentos agotados,
     `intervencion.md` en ese run y para.
4. Devuelve: los ids creados (el retorno del `arquitecto`, tal cual, tres líneas) y la orden
   siguiente, `/novela-continuar <slug>`.

**Hueco que la spec no cubre, y cómo se trata**: nada valida el plan del `trazador` antes del
primer capítulo. El primer `novela briefing <slug> 1 escritor` carga la ficha y saldría con 4 si
es inválida. Con la tabla de códigos de arriba, eso es `intervencion.md` y parada: el `trazador`
es de arranque y `/novela-continuar` no lo reintenta. Si la novela de humo lo encuentra, la
solución es un paso 3b aquí que reintente al `trazador`, y va a la spec como enmienda, no se
improvisa en el procedimiento.

**Revisión** (RF-13): los cuatro pasos en ese orden; el briefing del `trazador` antes de su Task;
el reintento es del `arquitecto`, no del `trazador`; la cuenta sale del log.

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
     y nombra el fichero. (El humano resuelve añadiendo esa línea. Es la convención más barata
     que distingue una intervención vieja de una viva.)
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
   `qa/NN-suspense.json`, y **solo ese campo**. Si alguno rechaza → reintento del `escritor` con
   `reintento:` esas dos rutas, y vuelta a 3.
7. `novela briefing <slug> <cap> cronista` → Task `cronista`, salida `estado/deltas/NN.json` →
   `novela aplicar-delta <slug> <cap>`. Sale con 1 → reintento del `cronista` con `causa:` = la
   causa de la última línea `aplicar-delta NN -> 1` de `harness.log`, y vuelta a `aplicar-delta`.
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

**Revisión** (RF-14): briefings de revisión antes de ninguna revisión; `validar` después del
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

## Al terminar la fase

- Lectura en seco: sobre un workspace de la fábrica (`uv run pytest` deja los de `conftest` en
  `tmp_path`; o `novela nueva prueba …` a mano), recorre `/novela-continuar` con el dedo, orden a
  orden, sin lanzar modelo. Cada orden existe, con los argumentos que el CLI acepta.
- No hay filas de trazabilidad todavía: RF-13 a RF-16 se aceptan con CA-10 en la fase 7.
