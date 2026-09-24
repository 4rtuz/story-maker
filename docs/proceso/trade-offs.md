# Trade-offs

Cada decisión relevante, con el mismo formato: opciones, criterios, elección y consecuencia. El
detalle está en la ADR o en el `decisions.md` que se cita.

## 1. Single-agent o multi-agent

- **Opciones.** (a) Un solo agente que planifica, escribe y se revisa. (b) Varios roles con
  contexto y herramientas propios.
- **Criterios.** Aislar el secreto del misterio. Que el crítico no comparta los sesgos del
  escritor. Coste por paso. Contexto acotado por invocación.
- **Elección.** (b), con los roles del patrón planner / writer / editor-critic:

  | Patrón | Roles | Modelo | Por qué ese reparto |
  |---|---|---|---|
  | Configuración | `entrevistador` | sonnet | Estructura lo que cuenta el cliente. Lo valida el CLI, no él |
  | Planner | `arquitecto` (canon y misterio) + `trazador` (escaleta y fichas) | opus + haiku | El canon condiciona toda la novela. El trazador ve el misterio y el escritor no: así se reparte la pista sin exponer la solución |
  | Writer | `escritor` | opus | La prosa es el producto. Nunca ve `canon/misterio.md` |
  | Editor / critic | `continuista` (hechos), `editor-estilo` (estilo), `lector-suspense` (tensión y fair play) | haiku | Tres críticos que verifican contra datos distintos, en paralelo |
  | Memoria | `cronista` | haiku | Extrae el delta de estado. Mecánico |

- **Consecuencia.** El invariante 3 tiene contención estructural. A cambio, el orquestador tiene
  que coordinar nueve pasos por capítulo, y cada rol se paga en cuota. En `main` el `Continuista`
  gastaba el 27 % del reloj con veredicto OK siempre; por eso ahora solo corre cuando el capítulo
  ya pasó el gate mecánico, que es gratis. Fuente: `docs/validators.md` §4.6, `architecture.md` §2.

## 2. Orquestador en Claude Code o con un SDK

- **Opciones.** (a) Python con el SDK de un proveedor. (b) Un framework de agentes. (c) Un bucle
  de shell. (d) Una sesión de Claude Code con subagentes.
- **Criterios.** Todo corre sobre la suscripción de Claude Code. Aislamiento por subagente.
  Testabilidad sin cuota.
- **Elección.** (d). El orden del bucle vive en `.claude/commands/novela-continuar.md`.
- **Consecuencia.** Contención por frontmatter y coste cero de infraestructura. Se acepta no
  controlar la temperatura, un techo de contexto por sesión (de ahí un capítulo por sesión en
  desatendido) y que la lógica del bucle sea markdown, sin tipos ni tests.
  [ADR 0001](../adr/0001-orquestador-en-claude-code.md).

## 3. Quién decide los gates

- **Opciones.** (a) La sesión, con reglas de lectura en prosa. (b) `cursor.intento` en la base.
  (c) Un `gates.jsonl` aparte. (d) Un subcomando `novela gate` que cuenta en `harness.log`.
- **Criterios.** La parada al tercer intento no puede depender de que un modelo cuente bien.
  Tiene que sobrevivir a una compactación. `estado.db` solo lo escribe `aplicar-delta`.
- **Elección.** (d). Motivo: en `humo-0003` la sesión informó 1 de 2 reintentos cuando el log
  daba 2 (F-31).
- **Consecuencia.** La parada pasa a ser código con tests y entra en el model checking. Introduce un
  código de salida nuevo (5). Saltarse el gate no lo impide nada en el momento, solo la auditoría
  de trayectoria. Hoy `novela-continuar.md` todavía cuenta en la sesión: `novela gate` es de la
  spec 0002, aceptada y sin implementar. [ADR 0002](../adr/0002-los-gates-los-decide-el-cli.md).

## 4. Formato de la story bible

- **Opciones.** (a) JSON o markdown en disco. (b) SQLite con un ORM. (c) SQLite con `sqlite3` de
  la stdlib, DDL a la vista y triggers.
- **Criterios.** Append-only de `libro_de_hechos` y `conocimiento` impuesto por el motor.
  Consultas por capítulo y entidad para los briefings. Sin dependencias nuevas.
- **Elección.** (c). `backend/novela/plataforma/esquema.sql`, tablas `STRICT`, triggers
  `BEFORE UPDATE/DELETE` con `RAISE(ABORT)`.
- **Consecuencia.** Ninguna ruta de escritura puede reescribir la historia, ni siquiera un
  `sqlite3` abierto a mano. `memoria/` es derivada y reconstruible. A cambio, corregir un hecho
  exige una versión nueva (§6). Spec 0001 §15, `architecture.md` §7.1.

## 5. Modelo de lectura

- **Opciones.** (a) Web servida por la API. (b) PDF generado por el CLI. (c) Epub ampliado.
- **Criterios.** El destinatario lo lee sin harness, sin servidor y sin red. Un solo fichero
  regalable. Enlaces internos y marcadores. Se prueba sin modelo. La API no escribe ni sale de
  `localhost`. Sin dependencias nativas en Windows.
- **Elección.** (b), con `fpdf2`: portada con dedicatoria, índice, capítulos y ficha enlazada
  desde la tabla `apariciones`.
- **Consecuencia.** Se prueba con `pypdf` en la suite. Se aceptan `fpdf2` LGPL y la revisión
  humana de la ficha antes de regalar. El cambio de un hecho se pide por CLI (`novela cambio`),
  no desde el PDF. La lectura web es complementaria ([`docs/lectura-web.md`](../lectura-web.md))
  y no sustituye al fichero. [ADR 0003](../adr/0003-entrega-del-libro-en-pdf.md).

## 6. Versiones de la novela

- **Opciones.** (a) Columna `version` en todas las tablas. (b) Capa de sustituciones. (c)
  Reescritura en sitio con excepción al invariante 7. (d) Una línea de tiempo nueva por versión.
- **Criterios.** No romper el append-only. Conservar la edición anterior verificable. Regenerar
  solo lo afectado.
- **Elección.** (d). `novela cambio` guarda la edición vigente en `versiones/vN/` y la base
  nueva se reconstruye: regenera con agentes los capítulos que usan el hecho y reaplica los demás
  byte a byte (`aplicar-delta --reaplicar`).
- **Consecuencia.** Nada ya escrito cambia de valor. El disco crece por versión. Un capítulo que
  menciona el hecho sin declararlo en el delta se reaplica tal cual. Un cambio a la vez.
  [ADR 0004](../adr/0004-versiones-de-la-novela.md), spec 0007.

## 7. TLA+ en el flujo real

- **Opciones.** (a) TLC en cada generación. (b) TLC en un test de pytest omitible. (c) TLC en un
  job propio de CI y en desarrollo.
- **Criterios.** TLA+ verifica el diseño del procedimiento, no una novela concreta. La suite del
  backend no necesita Java. Un fallo tiene que identificarse por su nombre.
- **Elección.** (c). El modelo cubre 5 capítulos y 2 reintentos, con el lock de dos procesos y
  la regeneración de la spec 0007.
- **Consecuencia.** Un cambio del procedimiento o del CLI que rompa «nada se publica sin pasar
  todos los validadores», «la reanudación no pierde ni duplica» o «toda generación termina» se ve
  en CI. El modelo puede divergir del markdown del procedimiento: lo mitiga un README que mapea
  cada acción al código. Spec 0013 D10, [`docs/formal/tla.md`](../formal/tla.md).

## 8. Invariantes de Lean, priorizados

- **Opciones.** (a) Los cuatro como obligatorios: orden temporal, edad/nacimiento, ubicuidad y
  exclusión. (b) Ubicuidad y nacimiento obligatorios, exclusión condicionada. (c) Solo ubicuidad.
- **Criterios.** Datos disponibles en `estado.db`. Falsos positivos. Coste de demostración.
- **Elección.** (b) en la spec. Ubicuidad (nadie en dos sitios a la vez) y nacimiento (nadie
  aparece antes de nacer) primero, porque solo necesitan lo que ya se registra. La exclusión va
  después, si se registran eventos que excluyen. Un orden estricto de escenas daba falsos
  positivos con cualquier analepsis.
- **Consecuencia.** El gate es obligatorio: sin toolchain, `comprobar-entorno` para antes del
  bucle. Sin Mathlib ni red. El test con Lean está marcado y se omite en CI. La integración añade
  tablas de cronología a `estado.db`. Spec 0012 D5, D9 a D11, [`docs/formal/lean.md`](../formal/lean.md).

## 9. Un workspace y un lock por novela

- **Opciones.** (a) Varias novelas en una base. (b) Un directorio por novela con su `estado.db`
  y un `state.lock`.
- **Criterios.** Aislar el daño de un fallo. Que el WAL no basta: `capitulos/`, `qa/` y `runs/`
  también se escriben.
- **Elección.** (b). `filelock` sin espera sobre `estado/state.lock`; ocupado sale con 3.
- **Consecuencia.** Un proceso por novela, fácil de razonar y de modelar en TLA+ (D8 de la 0013).
  Sin paralelismo entre capítulos de una misma novela. `backend/novela/plataforma/lock.py`.

## 10. Techo de 100.000 tokens por briefing

- **Opciones.** (a) Cargar todo lo que quepa en la ventana. (b) Truncar al llegar al límite.
  (c) Un techo por invocación, por debajo de la ventana, con degradación en orden fijo.
- **Criterios.** Un briefing truncado produce un capítulo plausible y contradictorio. El error
  de estimación sin endpoint de conteo. `CLAUDE.md` y `AGENTS.md` se pagan en cada subagente.
- **Elección.** (c). `briefing ≤ 100.000 − fijo (10.000) − salida − margen (15.000)`, estimado a
  3,5 caracteres por token, que es cota superior.
- **Consecuencia.** Recetas con presupuesto por agente y degradación declarada. Por eso
  `CLAUDE.md` no crece sin necesidad. `architecture.md` §6.5.

## 11. Modelo por rol

- **Opciones.** opus, sonnet o haiku en el frontmatter de cada agente. No hay temperatura.
- **Criterios.** Impacto del rol en la novela, frecuencia de invocación y si su salida la
  verifica código.
- **Elección.** Vigente en `.claude/agents/*.md`: opus para `arquitecto` y `escritor`, sonnet
  para `entrevistador`, haiku para `trazador`, `continuista`, `editor-estilo`, `lector-suspense`
  y `cronista`. El `trazador` y los revisores pasaron de opus y sonnet a haiku en `a414903`, por
  coste. `CLAUDE.md` y `architecture.md` §2.2 conservan la tabla anterior.
- **Consecuencia.** Menos coste por capítulo. Falta la medida del efecto en calidad: está en
  [`iteraciones.md`](iteraciones.md), pendiente de la evaluación de la spec 0014. `model: opus`
  es un alias: una actualización cambia el escritor sin que conste (`validators.md` §4.9, 6).

## 12. Langfuse por plugin o por SDK

- **Opciones.** (a) SDK de Langfuse en el orquestador. (b) Hook propio. (c) El plugin
  `langfuse-observability` (hooks `Stop` y `SessionEnd`) más scores emitidos por el CLI.
- **Criterios.** Sin SDK de modelos ni código de trazado que mantener. Claves fuera de git. Los
  datos personales del brief no se trazan.
- **Elección.** (c). El plugin se habilita solo en `.claude/settings.local.json`. `novela
  checkpoint` emite los scores por la API REST, con claves de `.env` que no llegan al entorno de
  ningún hijo. `/novela-brief` se abre con `--setting-sources project`, sin el plugin.
- **Consecuencia.** El trazado no captura el contexto ensamblado: los briefings de `runs/` son
  ese registro. La estructura session → turn → tool no es la ideal novela → capítulo → agente: se
  compensa con una sesión por capítulo y etiquetas por slug. Spec 0003 §15, `architecture.md`
  §10, [`docs/observabilidad.md`](../observabilidad.md).
