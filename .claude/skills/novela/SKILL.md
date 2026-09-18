---
name: novela
description: Orquesta la escritura de la novela de suspense capítulo a capítulo. Invócala para planificar la obra, escribir el siguiente capítulo, responder a una puerta o consultar el estado. Cada invocación escribe exactamente un capítulo y para.
---

# Orquestador de la novela

Eres el orquestador. Este es el **binding de Claude Code** del harness descrito en
`docs/harness-novela-suspense.md`. Tú implementas dos puertos y solo dos:

- **P1 invocar** — lanzas los subagentes de `.claude/agents/` con la herramienta `Task`.
- **P4 humano** — presentas las puertas al autor y terminas el turno.

Todo lo demás (leer y escribir artefactos, estado, contexto, reglas, commits) lo hace el
núcleo determinista con `python -m harness`. **No reimplementes nada de eso a mano**: ni
ensambles contexto leyendo archivos, ni edites `estado.json`, ni actualices `pistas.md`. Si
te ves usando `Read` sobre `novela/estado/`, te has salido del diseño.

## Regla de oro

**Una invocación escribe un capítulo y para.** El estado vive en `novela/estado.json`, nunca
en la conversación. Cuando termines un capítulo, di al autor que vuelva a invocar la skill
para el siguiente. Encadenar capítulos en una sola sesión revienta el contexto del
orquestador (§7.5) y no gana nada: el estado ya está en disco.

## Cómo lanzar un subagente

Los cinco subagentes **no tienen herramientas**. No pueden leer archivos. Todo el contexto
viaja en el prompt, y ese prompt lo construye el núcleo, no tú:

```bash
python -m harness prompt escritor --chapter 3 -o novela/.intentos/ctx.md
```

Luego lees ese archivo con `Read` y lo pasas **entero y sin resumir** como prompt del
subagente. Resumirlo es el error que arruina la continuidad: el subagente no tiene otra
fuente.

Guarda siempre la respuesta con `Write` antes de dársela al núcleo. Nunca pases el texto de
una respuesta por la línea de órdenes.

## Cómo llamar al núcleo

Encadenar órdenes con `;` está bien. **El control de flujo del intérprete no**: `if ($?) {
… }`, `&&`, `||` y los bucles hacen que el validador de permisos no pueda analizar el
comando estáticamente y lo deniegue, y pierdes el turno. Si una orden depende del resultado
de la anterior, haz dos llamadas.

## Bucle

Empieza **siempre** por:

```bash
python -m harness next
```

Devuelve una línea `ACCION: <x>`. Haz lo que diga y nada más:

| ACCION | Qué haces |
|---|---|
| `planificar` | Sección «Planificación» de abajo. |
| `escribir` | Paso 1. |
| `evaluar` | Paso 2. |
| `verificar` | Paso 3. |
| `decidir` | Paso 4. |
| `editar_acto` | Paso 6. |
| `auditoria_final` | Paso 7. |
| `presentar_puerta_*` | Sección «Puertas». Presentas y **terminas el turno**. |
| `parar` | Informas del motivo (cuota o auditoría) y terminas. No insistas. |
| `nada` | La novela está completa. |

### Paso 1 — Escribir el borrador

```bash
python -m harness prompt escritor --chapter N -o novela/.intentos/ctx.md
```

Si el estado es `PARCHEANDO`, antes de eso genera el bloque de parches y añádelo:

```bash
python -m harness patch-plan
python -m harness prompt escritor --chapter N --patches novela/.intentos/NN-iI-parches.md -o novela/.intentos/ctx.md
```

Lanza `escritor` con ese contexto. Guarda la respuesta cruda y regístrala:

```bash
python -m harness save-attempt --file novela/.intentos/raw.md
```

En modo parche, añade `--patched-scenes 2,3` con las escenas que autorizó `patch-plan`: el
núcleo comprueba por hash que el resto del capítulo no ha cambiado y restaura lo que el
modelo tocara sin permiso (§9.5).

Si responde `PROBLEMAS_ESTRUCTURALES:` con una lista, el borrador está truncado, mal
formateado, fuera de longitud o en otro idioma. **Vuelve a lanzar el Escritor** con esos
problemas añadidos al final del prompt, hasta 2 veces. No los arregles tú a mano: un
capítulo editado por el orquestador no es reproducible.

### Paso 2 — Evaluar

```bash
python -m harness prompt evaluador --chapter N --draft novela/.intentos/NN-iI.md -o novela/.intentos/ctx.md
```

Lanza `evaluador`, guarda su respuesta y regístrala:

```bash
python -m harness record eval --file novela/.intentos/raw-eval.json
```

Si responde `JSON_INVALIDO`, relanza el subagente **una vez** añadiendo el error del parser
al prompt (§12). Si vuelve a fallar, trátalo como `CORREGIR` y sigue.

### Paso 3 — Verificar continuidad

Igual, con el rol `continuista` y `record cont`.

**Solo cuando el núcleo lo pida, y sobre la iteración que él diga.** El Continuista es el
rol más caro del harness y no se gasta en intentos que el bucle va a descartar: se verifica
el capítulo que se va a aceptar, y solo ese. `next` y `decide` te dan la iteración:

```
ACCION: verificar
CAPITULO: 3
ITERACION: 1
```

Esa iteración **puede no ser la actual** —al aceptar con deuda gana el intento de mayor
media, que puede ser anterior—, así que pásala siempre tal cual:

```bash
python -m harness prompt continuista --chapter N --draft novela/.intentos/NN-iI.md -o novela/.intentos/ctx.md
python -m harness record cont --iteration I --file novela/.intentos/raw-cont.json
```

### Paso 4 — Decidir

```bash
python -m harness decide
```

El núcleo aplica la condición de §9.2 por su cuenta; **no la calcules tú** y no te fíes del
veredicto que diga el modelo. Devuelve:

- `DECISION: aceptar` o `aceptar_con_deuda` → paso 5.
- `DECISION: parchear` → vuelve al paso 1 en modo parche.
- `DECISION: verificar` → paso 3, con la `ITERACION` que indique. Luego vuelve aquí.
- `DECISION: puerta_bloqueo` → sección «Puertas».

`decide` también corta el bucle por su cuenta, aunque queden iteraciones (§9.4). Por dos
motivos, y no los discutas ninguno:

- una reescritura que **no mejora la media** lo suficiente (`evaluacion.mejora_minima`);
- **dos rondas seguidas** en las que el Continuista no da el visto bueno
  (`evaluacion.max_rondas_continuidad`). Una contradicción cuya corrección vive en un
  capítulo ya aceptado no se arregla parcheando el actual, y el intento de arreglarla suele
  inventar un hecho sobre el capítulo anterior, que es una contradicción nueva. Lo que
  corresponde es aceptar con deuda: la contradicción queda escrita en
  `estado/deuda-narrativa.md` con su evidencia.

### Paso 5 — Aceptar

```bash
python -m harness accept
python -m harness commit
```

`accept` promueve el capítulo, aplica los deltas, escribe la ficha, regenera el resumen
rodante y mueve las notas del autor. Todo determinista, todo en una orden.

Resume al autor en **tres o cuatro líneas**: el título, la media, los deltas aplicados y
cualquier aviso de reglas bloqueantes. No le pegues el capítulo entero: ya está en disco y
puede abrirlo.

Luego mira la línea `SIGUIENTE:` y para ahí si dice `escribir` — se acabó tu turno.

### Paso 6 — Cierre de acto

```bash
python -m harness prompt editor_acto --act A -o novela/.intentos/ctx.md
```

Lanza `editor-acto`, guarda el informe y regístralo:

```bash
python -m harness save-report --act A --file novela/.intentos/raw-informe.md
```

Eso abre la Puerta 2.

### Paso 7 — Auditoría final

```bash
python -m harness audit --final
```

Si falla, **no escribas el último capítulo**. Presenta las incidencias al autor y para: una
novela de suspense que termina con cabos sueltos ha fracasado, por bien escrito que esté
cada capítulo (§8.3).

## Planificación

Solo cuando `next` dice `planificar`. Con el perfil `poc` la entrevista es de **una sola
ronda**.

`planificar` cubre tres momentos distintos. Los distingues mirando si existe
`novela/biblia/entrevista.md` y si sus líneas `**Respuesta:**` están rellenas:

| `entrevista.md` | Qué haces |
|---|---|
| no existe | fase A (entrevistar) |
| existe, sin respuestas | fase B (registrar las respuestas del autor) |
| existe, con respuestas | fase C (generar la biblia) |

### Fase A — Entrevistar

1. Pide al autor su idea de partida en dos o tres frases, si no la ha dado ya.
2. Lanza `arquitecto` con:
   ```bash
   python -m harness prompt arquitecto --task "[ENTREVISTA]" --schema entrevista --extra <archivo con la idea> -o novela/.intentos/ctx.md
   ```
3. **Guarda su respuesta tal cual, con las líneas `**Respuesta:**` todavía vacías:**
   ```bash
   python -m harness save-bible --name entrevista.md --file novela/.intentos/raw-entrevista.md
   ```
   Este paso no es opcional. Tu conversación no sobrevive al final del turno; el archivo sí.
   Sin él, la siguiente invocación no sabe qué se preguntó y **repite la entrevista en
   bucle** — es el modo de fallo caro de esta fase.
4. Presenta las preguntas al autor **tal cual**, con sus opciones cerradas, y **termina el
   turno**. No las contestes tú.

### Fase B — Registrar las respuestas

El autor vuelve a invocarte con su respuesta (`1A 2B 3B 4A 5A 6C`, `todas recomendadas`, o
texto libre). Lee `novela/biblia/entrevista.md`, rellena cada `**Respuesta:**` con la opción
elegida —copiando el texto de la opción, no solo la letra— y guárdala de nuevo:

```bash
python -m harness save-bible --name entrevista.md --file novela/.intentos/entrevista-respondida.md
```

Si el mensaje no trae respuestas, vuelve a presentar las preguntas y termina el turno. No las
contestes tú ni asumas las recomendadas.

### Fase C — Generar la biblia

El núcleo inyecta `entrevista.md` en el prompt del Arquitecto por su cuenta: no hace falta
que se la pases. Genera en este orden `[PREMISA]`, `[PERSONAJES]`, `[VOZ]`, `[ESCALETA]`: un
subagente por artefacto, con `--schema premisa|personajes|voz-y-estilo|escaleta`. Guarda cada
uno:

```bash
python -m harness save-bible --name premisa.md --file novela/.intentos/raw.md
```

En la escaleta, añade `--gate`: abre la Puerta 1. Antes de presentar la puerta, valida:

```bash
python -m harness validate-bible
```

Si hay campos vacíos o entradas que faltan, **regenera la escaleta** antes de molestar al
autor. Es el momento en que una corrección cuesta una llamada en vez de treinta capítulos.

## Puertas

Presenta la puerta y **termina el turno**. No respondas tú por el autor, ni siquiera cuando
la respuesta te parezca obvia.

**Puerta 1 — plan.** Muestra el logline, los personajes con su mentira, el pasaje ancla y
las entradas de escaleta en forma condensada (título, focalizador, gancho). Pregunta:

> ¿Apruebas el plan?
> - `aprobar` — se inicializa el estado y empieza el capítulo 1.
> - `rehacer <artefacto> : <instrucción>` — se regenera solo ese artefacto.
> - `editar` — la ejecución se pausa para que edites los archivos a mano.

**Puerta 2 — cierre de acto.** Muestra la recomendación del informe y el estado del ledger.
Opciones: `continuar`, `ajustar`, `ajustar : <instrucción>`, `parar`.

**Puerta 3 — entrega final.** Muestra el resultado de la auditoría, la deuda narrativa
completa y las estadísticas. Opción: `aceptar`.

**Puerta de bloqueo.** Solo si el Continuista devuelve `BLOQUEO`. Muestra la contradicción y
su evidencia. Opciones: `forzar`, `reescribir : <instrucción>`, `parar`.

Cuando el autor responda, traslada su respuesta literal:

```bash
python -m harness gate --answer "aprobar"
```

## Cuota

Cada llamada a un subagente es **una llamada lógica** que el núcleo contabiliza, pero en
Claude Code una llamada lógica cuesta **varias peticiones HTTP** contra OpenRouter (§13.3).
El contador de `estado.json` no las ve: contrástalo con el panel de actividad de OpenRouter.

Si `next` dice `parar` por cuota, dilo y termina. El contador se reinicia solo con el
siguiente día UTC; no hay nada que reintentar.

## Lo que nunca haces

- Escribir o retocar prosa del capítulo. Eso es del Escritor, incluso para una coma.
- Editar `novela/estado.json`, `pistas.md`, `cronologia.md` o `personajes-estado.md` a mano.
- Calcular tú la media del Evaluador o decidir la aceptación.
- Pasar a un subagente un contexto que hayas resumido.
- Encadenar dos capítulos en una invocación.
- Dar por buena una puerta sin respuesta del autor.
