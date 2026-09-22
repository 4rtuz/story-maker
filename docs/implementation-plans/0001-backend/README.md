# Plan de implementación — spec 0001

Cómo se construye `backend/` desde cero. La spec `docs/specs/0001-backend-cli-estado-y-api.md`
dice **qué** hay que hacer y cómo se comprueba; este plan dice **en qué orden se teclea**, qué
test abre cada ciclo y dónde cae cada commit.

**Si el plan y la spec se contradicen, manda la spec.** Este directorio es ruta de ejecución, no
contrato. Cuando la spec pase a `implementada`, se borra.

## Los cuatro documentos

| Fase | Fichero | Qué construye | Utilizable al terminar |
|---|---|---|---|
| 1 | [fase-1-cimientos.md](fase-1-cimientos.md) | dominio, plataforma, `estado.db`, `nueva` · `estado` · `pendiente` | Un workspace creable e inspeccionable |
| 2 | [fase-2-bucle.md](fase-2-bucle.md) | `briefing` · `validar` · `aplicar-delta` · `checkpoint` | El bucle por capítulo, ejecutable de principio a fin |
| 3 | [fase-3-cierre.md](fase-3-cierre.md) | `auditar` · `exportar` | Una novela se puede cerrar y sacar en epub |
| 4 | [fase-4-api.md](fase-4-api.md) | los cinco `GET` y el OpenAPI commiteado | El frontend tiene de dónde generar sus tipos |

Cada fase se lee sola. Quien implemente la 2 no necesita abrir la 1 ni la 4: este README es lo
único que se lee siempre.

## Estado de partida

`backend/` está vacío. `git ls-files` devuelve once ficheros, todos Markdown salvo
`.claude/settings.json`. La primera línea de Python del proyecto es la tarea 1.1.

## Las cinco preguntas abiertas de §16, resueltas

`_plantilla.md` dice que una spec no se acepta con preguntas abiertas. Estas son **propuestas del
plan, pendientes de confirmación de arturo**. La spec no se toca hasta que confirme; entonces se
actualiza §16 y pasa a `aceptada` en un commit aparte.

| # | Pregunta | Decisión | Motivo | Si se decide lo contrario |
|---|---|---|---|---|
| 1 | ¿`novela nueva` o `novela init`? | **`nueva`** | El CLI ya mezcla verbos y sustantivos (`estado`, `briefing`, `checkpoint`, `pendiente`); `nueva` no desentona. `/novela-nueva` ya existe en tres documentos | Renombrar en la tarea 1.14 y en el slash command. Coste: una hora, y solo antes de que exista el primer workspace |
| 2 | ¿`presupuesto/` y `novela budget` como fase 5? | **No entra** | Sin una ejecución real no hay con qué calibrar umbrales, y la política de degradación la decide hoy el orquestador | Spec 0003 posterior, cuando la novela de humo dé números. No bloquea nada |
| 3 | ¿`run_id` lo genera el CLI o lo fija el orquestador? | **Los dos: `NOVELA_RUN_ID` si está definida, si no lo genera el CLI** | Tres líneas. Cierra `architecture.md` §12.2 alineando con el `session_id` de Langfuse, y hace deterministas las rutas de `runs/` en los tests — que es justo lo que el golden de CA-08 necesita | Si solo lo genera el CLI, el golden de CA-08 necesita otro mecanismo para fijar la ruta. Es la decisión más barata de las cinco y la que más paga |
| 4 | ¿La fase 4 ahora o al terminar la primera novela? | **Ahora, y la última** | Es la fase más barata: los modelos de respuesta ya existen desde la fase 1. Es además la única que puede posponerse sin bloquear el bucle | Se salta [fase-4-api.md](fase-4-api.md) y se retoma cuando exista frontend. El resto del plan no cambia |
| 5 | ¿Identificador de escena en el delta desde la fase 2? | **Sí** | Cuesta un campo. `linea_temporal` ya lleva `escena: "esc-07-2"` en §7.1 y los ids `esc-NN-N` ya están en `AGENTS.md`: no es una entidad nueva. No llevarlo convierte las dos capas baratas del índice (`architecture.md` §12.4) en una migración con reproceso | Si se decide que no, `indice_recuperable` deja de ser aditivo. Es la única de las cinco cuyo coste de revertir crece con cada capítulo escrito |

## Convenciones de ciclo

Aplican a todas las tareas de las cuatro fases. Escritas aquí una vez; las fases no las repiten.

**El ciclo, de `AGENTS.md`:**

1. **Spec primero** si el cambio tiene superficie. Ya la hay: es la 0001. Ninguna tarea de este
   plan necesita spec propia.
2. **Rojo.** Escribe el test y **ejecútalo para verlo fallar**. Un test que nunca has visto en
   rojo no prueba nada.
3. **Verde.** El mínimo código que lo pasa.
4. **Refactor** con la suite en verde.
5. `uv run pytest` completo, `mypy --strict` y `ruff` antes de commitear.

**Un commit es un ciclo cerrado. No se commitea en rojo.** Cada tarea de este plan lleva su
mensaje de commit sugerido; una tarea, un commit, salvo donde se diga lo contrario.

**Property-based, no de ejemplo**, en las cuatro funciones puras que la spec §13 nombra:
`gates.py`, `apply.py`, `violaciones.py` y `assemble.py`. Ahí los ejemplos no cubren
(`validators.md` §3.6). Las cinco propiedades de esa tabla son CA-09, CA-14, CA-18, CA-20 y CA-21.

**Ningún test llama a un modelo.** El bucle se prueba con un agente falso que escribe un capítulo
prefabricado desde `backend/tests/fixtures/`. CA-28 lo hace cumplir recorriendo el árbol de
imports.

**La frontera pura/impura no es estética.** `cmd.py` es la única cáscara imperativa de cada
slice: argumentos, lock, disco, código de salida. Si un fichero del núcleo importa `pathlib`,
`open`, `datetime.now` o red, está mal colocado — y el property-based deja de ser posible.

**Si cambias un modelo Pydantic**, en el mismo commit: regenera `backend/schemas/`, actualiza
`docs/definitions.md` y ajusta el test de contrato.

## Códigos de salida

Iguales para todos los subcomandos. De la spec §5.1; se repiten aquí porque toda tarea de CLI
los necesita.

| Código | Significado |
|---|---|
| 0 | Correcto. En `pendiente`, además: quedan capítulos |
| 1 | Gate fallido, hallazgos de auditoría, o en `pendiente`: no quedan capítulos |
| 2 | Uso incorrecto (lo emite Typer) |
| 3 | Lock ocupado: otro proceso trabaja sobre el workspace |
| 4 | Workspace inválido o estado ilegible |

## Matriz RF → fase → tarea

Los 27 requisitos funcionales de la spec §6, cada uno con la tarea que lo cierra.

| RF | Qué exige | Fase | Tarea |
|---|---|---|---|
| RF-01 | `novela nueva` crea árbol, `config.yaml` y `estado.db` | 1 | 1.14 |
| RF-02 | Triggers append-only en las cinco tablas | 1 | 1.9 |
| RF-03 | `filelock` y salida 3 | 1 | 1.12 |
| RF-04 | Escritura atómica y transacción | 1 | 1.11, 1.10 |
| RF-05 | `--breve` en ≤ 12 líneas | 1 | 1.15 |
| RF-06 | `--json` valida contra `state.schema.json` | 1 | 1.15 |
| RF-07 | `pendiente` comunica por código de salida | 1 | 1.16 |
| RF-08 | `briefing` ensambla e incrusta | 2 | 2.3, 2.6 |
| RF-09 | Aborto si el misterio se filtra | 2 | 2.4 |
| RF-10 | El misterio se incrusta para los tres que lo ven | 2 | 2.4 |
| RF-11 | Techo de contexto; nunca trunca | 2 | 2.5 |
| RF-12 | Degradación en orden fijo | 2 | 2.5 |
| RF-13 | Run y manifiesto | 2 | 2.1 |
| RF-14 | Los cinco gates de `validar` | 2 | 2.7 |
| RF-15 | Informe en `qa/NN-validacion.json` | 2 | 2.9 |
| RF-16 | Delta entero en transacción | 2 | 2.14 |
| RF-17 | Ids únicos y cursor monótono | 2 | 2.12 |
| RF-18 | Render de `memoria/resumenes/NN.md` | 2 | 2.15 |
| RF-19 | Idempotencia de `aplicar-delta` | 2 | 2.13 |
| RF-20 | `checkpoint` atómico | 2 | 2.17 |
| RF-21 | Seis scores por `ScoreSink` | 2 | 2.16 |
| RF-22 | Las cuatro comprobaciones de `auditar` | 3 | 3.1 |
| RF-23 | `exportar --formato md\|epub` | 3 | 3.2, 3.3 |
| RF-24 | Cinco `GET` en solo lectura | 4 | 4.3 |
| RF-25 | Slug validado antes de construir ruta | 4 | 4.2 |
| RF-26 | `schemas/` generados y versionados | 1 | 1.8 |
| RF-27 | Línea en `harness.log`, volcado línea a línea | 2 | 2.1 |

Los 29 criterios de aceptación van nombrados en la tarea que los cierra, dentro de cada fichero
de fase.

## Qué hay que arreglar por el camino

Cuatro desfases entre la documentación de referencia y lo que esta spec decide. La spec §14
manda corregirlos **en el mismo commit que el código que los cambia** — no al final, no en un
commit de limpieza.

| Qué | Dónde | Commit de destino |
|---|---|---|
| `backend/novela/models/` → `dominio/` | `AGENTS.md`, `validators.md` §3.1 | Tarea 1.2, el primer commit que crea `dominio/` |
| `qa/NN-informe.md` → `qa/NN-<agente>.json` | `definitions.md` §6 | Tarea 1.7, con `qa.py` |
| Aparece `novela nueva` en la lista de subcomandos | `architecture.md` §8, `AGENTS.md` | Tarea 1.14 |
| El `cronista` deja de escribir `memoria/resumenes/NN.md` | `architecture.md` §7.5 | Tarea 2.15 |

Y una cosa que no es desfase sino agujero: **`.gitignore` tiene una sola línea** (`.local.env`) y
no ignora `novelas/`, que `AGENTS.md` declara ignorado. Se arregla en la tarea 1.1, que es lo
primero que se hace, porque un `git add -A` antes de eso versiona un workspace entero.

## Huecos de la documentación que la implementación va a encontrar

Ninguno bloquea: los cuatro tienen resolución propuesta en su tarea. Se listan aquí porque son
los que cuestan un día si aparecen con el código ya escrito.

1. **No hay DDL en ningún sitio.** `architecture.md` §7.1 dice «una tabla por colección de la
   rama 4» y enseña un trigger de ejemplo. Nada más. → tarea 1.9.
2. **`definitions.md` y el contrato serializado de §7.1 no coinciden en ocho nombres de campo**
   de la rama 4, ni en la forma de `cursor`. Mandan los de §7.1: son los que salen por la API y
   los que tendrán tabla. → tarea 1.6.
3. **No existe ni un ejemplo del delta del `cronista`**, y es la única entrada de
   `aplicar-delta`. Su forma hay que derivarla. → tarea 2.11.
4. **Faltan cinco de las siete recetas** de `config/recipes.yaml`: §6.2 solo trae `escritor` y
   `continuista`. → tarea 2.2.

## Qué queda fuera

De la spec §1, y no se toca en ninguna fase:

- **Todo `.claude/`**: los siete agentes, los tres slash commands, los dos hooks y el bloque de
  permisos. Hoy `.claude/` contiene un único fichero con plugins de desarrollo. Es la otra mitad
  del sistema y necesita su propia spec.
- El **contenido** de los prompts de los agentes. Esta spec fija el mecanismo de ensamblado y el
  formato de las recetas, no qué dice cada prompt.
- El slice `presupuesto/` y `novela budget` (`architecture.md` §9).
- Las cuatro decisiones abiertas de `architecture.md` §12: `indice_recuperable` (§12.4), los dos
  `GET` del log en vivo (§12.6), la cola en disco y `run.sh` (§12.8), y la regla `deny` sobre el
  misterio (§12.7).
- El **frontend**. Consume el OpenAPI que produce la fase 4, y nada más.

## Trabajo siguiente

La spec 0001 excluye `.claude/` por diseño, y `.claude/` está vacío: cero agentes, cero hooks,
cero slash commands. Mientras siga así, `architecture.md` §6.3 y §7.4 describen el contrato de
los agentes, no lo que hay en disco. Es una spec 0002, y no depende de que esta termine: puede
escribirse en paralelo.
