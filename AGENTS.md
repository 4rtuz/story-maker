# AGENTS.md

Convenciones del harness de generación de novelas de suspense. Léelo antes de actuar.

Documentación de referencia, solo cuando la necesites: `docs/architecture.md` (stack y estructura), `docs/definitions.md` (qué significa cada entidad), `docs/domain-knowledge.md` (diagramas), `docs/validators.md` (cómo se verifica cada cosa y qué riesgos están aceptados).

## Qué es este proyecto

Un sistema multiagente que escribe una novela de suspense completa a partir de una idea inicial. Los roles se reparten el trabajo: `arquitecto`, `trazador`, `escritor`, `continuista`, `editor-estilo`, `lector-suspense` y `cronista`, y en una novela de regalo, antes, el `entrevistador`. Un orquestador los invoca en un bucle por capítulo y aplica gates de calidad entre paso y paso.

## Monorepo

Dos carpetas grandes. Todo lo demás en la raíz es compartido.

| Carpeta | Stack | Qué hace |
|---|---|---|
| `backend/` | Python 3.12, FastAPI, Typer, Pydantic v2, `uv` | CLI `novela` (escribe) y API REST (`backend/api/`: lee, y lanza el CLI) |
| `frontend/` | Vite + TypeScript + Three.js | Panel: consulta la API y lanza novelas a través de ella |

Reglas:

- El backend es lo único que toca `novelas/<slug>/`. El frontend nunca lee el disco: pasa por la API.
- La API **no escribe en ningún workspace**. Sus únicos `POST` son los de `/lanzamientos`, que lanzan `novela producir` en segundo plano; mutar sigue siendo trabajo del CLI. Si hace falta escribir, se añade un subcomando al CLI y, si el panel debe dispararlo, un paso de `producir`, nunca una orden libre.
- `/lanzamientos` ejecuta `claude` sin preguntar: solo admite loopback, `Host` local y `Origin` del panel, cuerpo JSON validado, y un lanzamiento a la vez. No relajes esas guardas; sus tests están en `backend/tests/test_lanzamientos.py`.
- Los modelos Pydantic de `backend/novela/dominio/` son también los de respuesta de la API. Una sola ontología.
- FastAPI no contradice el «nunca añadir un SDK de API»: esa regla es sobre proveedores de modelos, y la API no llama a ninguno.

Detalle de endpoints y arranque: `docs/architecture.md` §11.

## Separación repo / workspace

- El repositorio es el harness: `backend/`, `frontend/`, `docs/` y las definiciones de agentes.
- `novelas/<slug>/` son datos de una novela. Está en `.gitignore`. Nunca lo versiones ni lo edites a mano.

## Las cuatro ramas de contexto

No las mezcles. Confundirlas es la causa más común de incoherencia.

| Directorio | Qué es | Cómo cambia |
|---|---|---|
| `canon/` | Lo que es verdad del mundo | Versionado; solo el orquestador autoriza cambios |
| `plan/` | Lo que debería pasar | Versionado |
| `estado/estado.db` | Lo que ya pasó | Fuente única de verdad; SQLite |
| `memoria/` | Resúmenes derivados | Reconstruible; nunca fuente de verdad |

## Invariantes

Estas reglas no se negocian. Si una tarea parece exigir romper una, para y pregunta.

1. **`estado/estado.db` es la única fuente de verdad sobre lo escrito.** Base SQLite; no la abras para escribir: se actualiza con `novela aplicar-delta`. Para leerla, `novela estado`.
2. **`libro_de_hechos` y `conocimiento` son append-only.** Modificar o borrar una entrada existente es reescribir la historia y rompe toda verificación posterior. Solo se añaden entradas; sus tablas tienen triggers que abortan cualquier `UPDATE` o `DELETE`.
3. **`canon/misterio.md` es secreto.** El `escritor` y el `editor-estilo` no lo leen nunca. Reciben solo las pistas listadas en la ficha de su capítulo.
4. **Fair play.** Ninguna revelación sin al menos una pista plantada antes.
5. **El contexto vive en disco, no en la conversación.** Nunca reconstruyas estado a partir de una sesión previa; léelo de `estado.db` y `checkpoints/`.
6. **Escritura atómica.** Todo fichero se escribe en `.tmp` y se renombra. El estado es la excepción: `estado.db` se escribe en una transacción, nunca por copia de fichero.
7. **No se reescriben capítulos de una versión.** Si el problema del capítulo 7 nace del 5, para y pide intervención. Solo `novela cambio` abre una versión nueva, y la anterior queda intacta en `versiones/`.
8. **Un proceso por workspace.** Respeta `estado/state.lock`.

## Cómo trabaja cada rol

Cada agente recibe un *briefing* generado para esa invocación concreta en `runs/<run_id>/briefings/NN-<agente>.md`. Reglas comunes:

- Lee solo el briefing y las rutas listadas dentro de él. No explores el workspace por tu cuenta.
- Escribe solo en las rutas declaradas como salida.
- Devuelve un informe breve. Los hallazgos completos van a `qa/`, no al canal de retorno.
- Ante ambigüedad, falla explícitamente. No inventes.
- Salida estructurada donde el contrato lo pida: JSON válido contra su esquema en `backend/schemas/`, sin prosa alrededor ni vallas de código.

## CLI

Operaciones deterministas. No llaman a ningún modelo y no consumen cuota.

```
novela nueva <slug> --idea "..."      crea el workspace y estado.db
novela nueva <slug> --brief           lo mismo, con la obra derivada de brief/brief.json
novela estado <slug> --breve          cursor, hilos abiertos, capítulos hechos
novela estado <slug> --json           estado completo serializado, para inspección
novela briefing <slug> <cap> <agente> genera el contexto de una invocación
novela validar <slug> <cap>           esquema, longitud, pistas presentes, hilos
novela aplicar-delta <slug> <cap>     única vía de escritura de estado.db
novela checkpoint <slug> <cap>
novela validar-plan <slug>            escaleta y fichas: el gate del trazador
novela pendiente <slug>               salida 0 si quedan capítulos
novela auditar <slug>                 pistas huérfanas, hilos sin cerrar
novela exportar <slug> --formato md|epub|pdf
novela comprobar-entorno [--limpio]   hook, python, settings.local.json y .env antes de lanzar
novela producir <slug> [--idea "..."] la novela entera, una sesión de claude por paso; sin idea, reanuda
novela brief iniciar <slug> --ocasion <o>            novela de regalo: workspace del brief
novela brief entrada <slug> --tipo <t> --fichero <f> ingiere lo que aporta el cliente
novela brief preparar <slug>                         briefing del entrevistador
novela brief validar <slug>                          informe y, si valida, brief.json
novela cambio <slug> --hecho <hec> --texto "..." [--simular]   versión nueva; --siguiente: qué toca
novela versiones <slug> [--novedades | --verificar | --diff vA vB --capitulo N]   solo lectura
```

Ejecuta `novela validar` antes de invocar a ningún agente de revisión: detecta gratis lo que no merece una llamada a un modelo.

## Identificadores

Prefijo de tipo más slug o secuencia. Son claves estables: el nombre visible de un personaje puede cambiar en la trama, su id no.

```
per-elena-vidal   personaje       pis-007   pista
esc-casa-del-faro escenario       pfa-003   pista falsa
esc-01-3          escena          rev-002   revelación
hil-004           hilo            hec-014   hecho
obj-011           objeto o prueba cap-01    capítulo
cam-001           cambio
```

`esc-` sirve a escenario y a escena: escenario lleva letra tras el guion (`esc-casa-del-faro`),
escena lleva dígito (`esc-01-3`). Las expresiones que los validan son disjuntas.

Capítulos con dos dígitos (`01`) hasta 99; tres si la novela pasa de 99, y entonces en todo el workspace desde el inicio. No se mezclan formatos.

## Proceso: generar código (TDD)

Ciclo obligatorio. No hay excepción por «es un cambio pequeño».

1. **Spec primero** si el cambio tiene superficie: subcomando nuevo, endpoint, campo de esquema, contrato de agente. Si es un arreglo interno sin superficie, salta al paso 2.
2. **Rojo.** Escribe el test y **ejecútalo para verlo fallar**. Un test que nunca has visto en rojo no prueba nada.
3. **Verde.** El mínimo código que lo pasa.
4. **Refactor** con la suite en verde.
5. `uv run pytest` completo, `mypy --strict` y `ruff` antes de commitear; en `frontend/`, `npm run verificar`.

Reglas propias del proyecto:

- **Ningún test llama a un modelo.** El bucle se prueba con un agente falso que escribe un capítulo prefabricado desde `backend/tests/fixtures/`.
- Si tocas un gate de `validate.py` o una rama de `delta.py`, el test es property-based, no de ejemplo: ahí los ejemplos no cubren (`docs/validators.md` §3.6).
- Si cambias un modelo Pydantic: regenera `backend/schemas/` (`REGENERAR=1 uv run pytest tests/test_contratos.py`), actualiza `docs/definitions.md` y ajusta el test de contrato, todo en el mismo commit.
- **Cambiar el prompt de un agente no es código y no tiene TDD**: no es determinista. Va por spec y se valida con una novela de humo de 3 capítulos comparando scores.

Un commit es un ciclo cerrado. No se commitea en rojo.

## Proceso: modificar documentación

Cinco tipos de documento, cinco reglas. No los mezcles.

| Documento | Qué describe | Cuándo se toca |
|---|---|---|
| `AGENTS.md`, `CLAUDE.md` | Convenciones vigentes | Solo si cambia una convención |
| `docs/architecture.md`, `definitions.md`, `domain-knowledge.md`, `validators.md` | El estado **actual** del sistema | En el mismo commit que el código que lo cambia |
| `docs/specs/NNNN/spec.md`, `decisions.md` | Un cambio concreto **antes** de existir, y sus decisiones | Al proponerlo |
| `docs/specs/NNNN/plan/`, `validators.md` | Cómo se ejecuta una spec aceptada y dónde puede fallar | Al aceptarla; se borran al implementarla, tras subir a `docs/validators.md` lo que perdura |
| `docs/adr/NNNN-<slug>.md` | Una decisión con alternativas descartadas | Cuando revertirla sería caro |

**Regla dura: la documentación de referencia describe lo que hay, no lo que habrá.** Nada de «próximamente» o «pendiente» en `architecture.md`. El futuro vive en `docs/specs/`.

Ciclo de vida de una spec:

1. Crea `docs/specs/NNNN/` con `spec.md` y `decisions.md`, correlativo de cuatro dígitos. Estado `borrador`. Las specs anteriores a la 0004 conservan su formato (`docs/specs/NNNN-<slug>.md` y `docs/implementation-plans/NNNN-<slug>/`) hasta cerrarse.
2. Se discute **en el fichero**, no en la conversación: la conversación se pierde y el fichero es lo que lee el siguiente agente.
3. Aceptada → estado `aceptada`, con `plan/` (un `README.md` y un fichero por fase) y `validators.md` escritos. Sus criterios de aceptación son los tests del ciclo TDD, uno a uno. Una spec sin criterios verificables no se acepta.
4. Implementada → estado `implementada`, sha del commit en el frontmatter, y en ese mismo commit se actualizan los docs de referencia que quedaron desfasados: lo que perdura de `validators.md` sube a `docs/validators.md` y se borran `plan/` y `validators.md`.
5. Descartada → estado `descartada` con el motivo. **No se borra**: el motivo es lo que evita que alguien la reproponga en tres meses.

Una spec que lleva dos versiones del harness en `borrador` está muerta. Ciérrala como `descartada`.

## Proceso: ejecución

**Puesta en marcha**

```bash
cd backend  && uv sync                              # Python 3.12
cd frontend && npm install
```

Una vez por máquina, para poder lanzar el harness:

1. `uv` en el PATH de usuario, de forma persistente: lo necesitan `uv tool` y el hook del plugin de Langfuse.
2. `uv tool install --editable ./backend` desde la raíz: deja `novela` en `~/.local/bin`.
3. Abrir `claude` una vez en la raíz del repo y aceptar el diálogo de confianza: sin ella, `claude -p` ignora el `allow` del proyecto.

Las claves de los scores, si se quieren, van en `.env` en la raíz, que git ignora.

**Desarrollo**

```bash
cd backend  && NOVELAS_DIR=../novelas uv run uvicorn api.main:app --reload  # API
cd frontend && npm run dev                           # panel, consume la API
cd backend  && uv run pytest                         # sin llamadas a modelo, sin cuota
```

**Escribir una novela.** Desde el panel (`#/lanzar`): un clic lanza `novela producir`, que hace el bucle desatendido de abajo de principio a fin —`/novela-nueva`, un `/novela-continuar` por capítulo y `/novela-auditar`— y se detiene o reanuda desde la misma vista. La API tiene que servir `<repo>/novelas`, o se niega a lanzar. A mano, lo mismo es `novela producir <slug> --idea "..."` desde la raíz.

Interactivo, en una sesión del harness y con `/clear` entre actos. La sesión se abre aislada del ámbito de usuario y con la variable que activa la regla 5 del hook; las sesiones de desarrollo del harness no la exportan:

```bash
export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
claude --session-id "$NOVELA_SESSION_ID" --setting-sources project,local --model opus
```

Dentro de ella:

```
/novela-nueva <slug> --idea "..." --capitulos 24 --palabras 80000
/novela-continuar <slug>
/novela-auditar <slug>
```

Desatendido, una sesión por capítulo para acotar el contexto y el daño de un fallo. En Git Bash:

```bash
export MSYS_NO_PATHCONV=1                 # sin esto, "/novela-continuar" llega como ruta de Windows
export CC_LANGFUSE_TRACE_TAGS=<slug>
export CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS=30000   # sin esto, -p pierde el último turno
novela comprobar-entorno || exit 1
while novela pendiente <slug>; do
  antes=$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)
  export NOVELA_SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
  export CC_LANGFUSE_TRACEPARENT=$(novela traza <slug> /novela-continuar)   # docs/observabilidad.md
  claude -p "/novela-continuar <slug> --capitulos 1" --session-id "$NOVELA_SESSION_ID" \
    --setting-sources project,local --permission-mode dontAsk --model opus || break
  [ "$(cat novelas/<slug>/checkpoints/latest.json 2>/dev/null)" != "$antes" ] || break
done
```

El `|| break` es deliberado: ante un error el sistema para y deja el checkpoint, no insiste. `comprobar-entorno` para antes de la primera sesión, y la última línea, si una sesión no avanza el checkpoint. Para reanudar, vuelve a lanzarlo — `/novela-continuar` lee `checkpoints/latest.json` y repite el último paso no confirmado. Nunca reconstruyas el estado desde una conversación previa.

Si el bucle escribe `runs/<run_id>/intervencion.md`, ha agotado los intentos de un gate y necesita una decisión humana. Léelo antes de relanzar nada.

El CLI no accede a la red salvo para emitir scores a Langfuse.

## Nunca

- Añadir un proveedor de modelos, un gateway o un SDK de API de modelos. Todo corre sobre la suscripción de Claude Code.
- Dar al frontend acceso directo al workspace, o a la API capacidad de escribir en él o de ejecutar algo distinto de `novela producir`.
- Escribir claves en ficheros versionados.
- Dejar prosa dentro de un fichero que el contrato define como JSON.
- Ampliar `CLAUDE.md` o este fichero sin necesidad: se cargan en cada sesión y en cada subagente, y cada línea se paga muchas veces.
