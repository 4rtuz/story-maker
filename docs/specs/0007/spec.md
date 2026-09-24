---
id: 0007
titulo: Regenerar los capítulos que usan un hecho cambiado y versionar la novela
estado: implementada
sha: el commit de cierre de T5.3, cabeza de la rama spec-0007
demostracion: T5.2 sin ejecutar; necesita una sesión humana del harness (docs/validators.md §4.9)
version: 2
fecha: 2026-09-24
specs_relacionadas: [0001, 0002, 0003, 0005, 0006]
---

# 0007 — Regenerar los capítulos que usan un hecho cambiado y versionar la novela

## 1. Resumen

El operador pide por CLI, en nombre del lector, que un hecho de la novela pase a ser otro. `novela cambio` registra la petición y calcula en `estado.db` qué capítulos usan ese hecho. Después guarda la edición vigente como versión inmutable y prepara una versión nueva. En ella el bucle existente regenera solo esos capítulos y reaplica, byte a byte, los demás. Al terminar, `novela versiones` y la exportación en markdown marcan qué capítulos cambiaron respecto a la versión anterior, que se conserva siempre intacta.

## 2. Contexto y problema

**Hoy un hecho no se puede cambiar.** `libro_de_hechos(id, texto, capitulo, cita)` de `backend/novela/plataforma/esquema.sql` guarda un solo capítulo por hecho, el de origen. Además es append-only por trigger (`AGENTS.md` § Invariantes 2, `docs/architecture.md` §7.1). Ninguna tabla dice qué capítulos posteriores se apoyan en un hecho. `conocimiento` y `conocimiento_lector` lo referencian por `hecho` y `desde_capitulo`, pero una mención sin conocimiento nuevo («el faro seguía apagado») no deja rastro. La auditoría del entregable (`docs/auditoria-entregable.md` § LEC) marca LEC-05 a LEC-08 como «falta».

**Las restricciones del repositorio chocan con regenerar.**

- El invariante 7 de `AGENTS.md` dice «No se reescriben capítulos anteriores», y `docs/architecture.md` §12.5 lo justifica: la reescritura retroactiva «invalidaría el estado y los resúmenes de todo lo intermedio». El sello de la spec 0001 (RF-35) hace que `novela briefing` salga con 4 si cambia un capítulo cerrado.
- `estado.db` solo se escribe con `novela aplicar-delta`, en una transacción (`AGENTS.md` § Invariantes 1 y 6). Cinco tablas son append-only, y algunas tienen claves que un capítulo regenerado repetiría: `linea_temporal.escena` y `tension_real.capitulo` (`esquema.sql`). `violaciones.py` rechaza además un delta de un capítulo anterior al cursor. Sobre la base vigente no se puede volver al capítulo 5 sin borrar o reescribir filas.
- La API es de solo lectura y mutar es un subcomando del CLI (`AGENTS.md` § Monorepo).
- `docs/validators.md` §4.14 ya define el estado como reproducible: aplicar en orden `estado/deltas/*.json` sobre una base vacía. Esta spec se apoya en esa definición (ver D1).

**No hay versiones.** `docs/validators.md` §5.7 acepta que «el único rollback de datos es `checkpoints/`», y el checkpoint no guarda la base (§4.14). Hoy no existe ninguna copia de una edición anterior de la novela.

**Relación con otras specs.**

- **0001** fijó `aplicar-delta`, la custodia (RF-30 a RF-32), la cita literal (RF-33), el sello (RF-35) y los códigos de `backend/novela/plataforma/salida.py`. Esta spec añade un modo `--reaplicar` que sustituye la custodia de briefings por la de la instantánea (ver D11), y no cambia el modo normal fuera de una regeneración.
- **0002**, aceptada y sin implementar, añade `novela gate`, la auditoría de trayectoria e invariantes a `aplicar-delta`. Su máquina de trayectoria tendrá que admitir la secuencia `aplicar-delta --reaplicar` → `checkpoint`, sin `escritor` (§10, §11).
- **0003** fijó el hook y el contrato de `.claude/`. Esta spec cambia el cuerpo de tres agentes y el procedimiento `novela-continuar`, sin añadir roles ni herramientas.
- **0005** (Propuesta) añade `brief/`. Una versión nueva no lo copia ni lo cambia (ver D8).
- **0006** (Propuesta) añade la tabla `apariciones`, derivada en `aplicar-delta` con el mismo patrón que `usos_de_hecho` (tabla aparte, append-only, fuera de la vista `Estado`, sin backfill). También añade el PDF y reserva `docs/adr/0003-…`. La página de novedades en PDF de LEC-07 depende de ella (ver D18), y el ADR de esta spec es el 0004 (ver D2).

## 3. Objetivos y no objetivos

### 3.1 Objetivos

- **O-01** `novela cambio <slug> --hecho <hec-id> --texto "<nuevo>"` registra la petición y prepara una versión nueva. Imprime los capítulos que la regeneración reescribirá y los que conservará.
- **O-02** `estado_db.capitulos_que_usan(conn, hecho)` devuelve, con una consulta indexada sobre la tabla `usos_de_hecho`, el 100 % de los capítulos que introducen, hacen saber o citan el hecho.
- **O-03** Tras regenerar con el bucle existente, los capítulos no afectados de la versión nueva son idénticos byte a byte a los de la anterior. El paso a la versión nueva no rompe la continuidad: 0 deltas reaplicados rechazados por `violaciones` sin intervención.
- **O-04** La versión anterior queda en `versiones/vN/`, idéntica byte a byte a la edición vigente antes del cambio, y ningún subcomando la modifica después.
- **O-05** `novela versiones` y `novela exportar --formato md` listan y marcan los capítulos cambiados respecto a la versión anterior, con un enlace interno por capítulo.
- **O-06** `docs/adr/0004-versiones-de-la-novela.md` documenta cómo convive la regeneración con los invariantes 2 y 7. `AGENTS.md`, `docs/architecture.md`, `docs/definitions.md` y `docs/validators.md` describen lo implementado en el mismo commit que el código.
- **O-07** `uv run pytest`, `mypy --strict` y `ruff` en verde, sin tests que llamen a un modelo y sin cambios en `backend/api/openapi.json` ni `backend/schemas/state.schema.json`.

### 3.2 No objetivos

- La UI web y cualquier formulario del panel. El frontend no cambia y la API no gana rutas, ni de lectura (ver D19).
- Cambiar algo que no sea un hecho de `libro_de_hechos`: personajes, relaciones, canon, pistas, revelaciones o el plan (ver D21).
- Modificar `canon/` o `plan/` al regenerar. Las fichas de plan de los capítulos afectados siguen siendo las mismas (ver D21).
- Regenerar en cascada los capítulos que usan hechos de un capítulo afectado. La continuidad la garantizan los hechos requeridos (ver D13, D14).
- Más de un cambio a la vez, o un cambio sobre una novela sin terminar (ver D6).
- Rellenar `usos_de_hecho` en workspaces anteriores a esta spec (ver D5).
- Volver a una versión anterior (rollback) o borrar versiones. Solo se crean y se leen.
- La página de novedades en epub. En PDF solo si la spec 0006 está implementada (ver D18).
- Deshacer la parada por el invariante 7 que ya existe: un problema retroactivo detectado por un gate sigue acabando en `intervencion.md` (ver D2).

## 4. Usuarios y escenarios

| Actor | Relación con esta spec |
|---|---|
| Lector de la novela | Pide el cambio de un hecho. No usa el harness |
| Operador humano | Traduce la petición a `novela cambio`, lanza la regeneración y entrega la versión nueva |
| Orquestador (sesión principal) | Sigue `/novela-continuar`, que consulta `novela cambio --siguiente` y reaplica o regenera cada capítulo |
| `escritor`, `continuista`, `cronista` | Reciben en su briefing la capa `cambio` en los capítulos afectados |
| CLI `novela` | Registra usos, prepara versiones, reaplica, valida la regeneración y lista novedades |

- Como lector, quiero que el hecho que pedí cambiar sea distinto en todos los capítulos que lo usan, y que el resto de la novela siga igual, para leer una versión coherente sin releer lo que no cambió.
- Como operador, quiero ver antes de gastar cuota qué capítulos se van a regenerar, y conservar siempre la edición anterior, para poder entregarla si la nueva no convence.
- Como desarrollador del harness, quiero probar la consulta, la regeneración selectiva y la inmutabilidad de la versión anterior con un agente falso, para mantener la suite sin cuota.

## 5. Requisitos funcionales

**Usos de hechos en `estado.db`**

| ID | Requisito (EARS) | Prioridad |
|----|------------------|-----------|
| RF-01 | El sistema debe definir en `backend/novela/plataforma/esquema.sql` la tabla `STRICT` `usos_de_hecho (hecho TEXT NOT NULL, capitulo INTEGER NOT NULL, via TEXT NOT NULL CHECK (via IN ('origen','conocimiento','lector','cita')), PRIMARY KEY (hecho, capitulo, via))`, con el índice `usos_por_capitulo` y triggers `BEFORE UPDATE` y `BEFORE DELETE` que abortan con «usos_de_hecho es append-only» (ver D3). | Must |
| RF-02 | El sistema debe añadir a `Delta` el campo `hechos_usados: list[UsoCitado]`, con `[]` por defecto, donde `UsoCitado` es `{hecho: HechoId, cita: str}`. Toda `cita` debe ser literal del cuerpo del capítulo con la normalización de la spec 0001 (RF-33). El `hecho` debe existir en `libro_de_hechos` vigente o en el propio delta (ver D4). | Must |
| RF-03 | Cuando `novela aplicar-delta <slug> N` aplique un delta, el sistema debe registrar en `usos_de_hecho`, en la misma transacción que `estado_db.guardar`, una fila `(h, N, 'origen')` por cada hecho de `delta.libro_de_hechos`, `(h, N, 'conocimiento')` por cada entrada de `delta.conocimiento`, `(h, N, 'lector')` por cada entrada de `delta.conocimiento_lector` y `(h, N, 'cita')` por cada entrada de `delta.hechos_usados` (ver D3). | Must |
| RF-04 | Cuando `aplicar-delta` se repita sobre el mismo capítulo, el sistema no debe duplicar ni borrar filas de `usos_de_hecho` (ver D3). | Must |
| RF-05 | Cuando `aplicar-delta` abra un `estado.db` sin la tabla `usos_de_hecho`, el sistema debe crearla con su índice y sus triggers (DDL idempotente) dentro de la misma transacción, antes de registrar (ver D5). | Should |
| RF-06 | El sistema debe ofrecer `estado_db.usos(conn, hecho) -> list[UsoDeHecho]` y `estado_db.capitulos_que_usan(conn, hecho) -> list[int]`, con los capítulos distintos en orden ascendente. Las dos deben funcionar sobre una conexión abierta en solo lectura y lanzar `EstadoIlegible` si la tabla no existe (ver D3). | Must |
| RF-07 | Mientras `estado.db` no tenga la tabla `usos_de_hecho`, `novela estado` y `GET /novelas/{slug}/estado` deben responder lo mismo que antes de esta spec (ver D3). | Must |

**Petición de cambio**

| ID | Requisito (EARS) | Prioridad |
|----|------------------|-----------|
| RF-08 | Cuando se ejecute `novela cambio <slug> --hecho H --texto T --simular`, el sistema debe imprimir el id reservado para el hecho nuevo, los capítulos a regenerar, los hechos requeridos de cada uno y los capítulos a reaplicar. No debe escribir ningún fichero y debe salir con 0 (ver D13, D15). | Must |
| RF-09 | Cuando se ejecute `novela cambio <slug> --hecho H --texto T [--motivo M]` sin `--simular`, el sistema debe registrar la petición en `cambios/cam-NNN.json` con `WorkspaceRepository.escribir`. Debe preparar la versión nueva (RF-17 a RF-19), imprimir `cambio cam-NNN: H → <id reservado> · versión N+1 · regenerar <lista> · reaplicar <n> capítulos` y salir con 0 (ver D7, D22). | Must |
| RF-10 | Si al pedir un cambio la novela no está terminada (`checkpoints/latest.json` ausente o con `capitulo` menor que `num_capitulos`), hay un cambio en curso o existe un `runs/*/intervencion.md` sin línea `resuelto:`, entonces el sistema debe salir con 1, nombrar la causa y no escribir nada (ver D6). | Must |
| RF-11 | Si `H` no casa `^hec-\d{3}$` o no está en `libro_de_hechos` vigente, o `T` queda vacío tras quitar espacios, supera 500 caracteres o coincide con el `texto` vigente de `H` tras normalizar a NFC y colapsar espacios, entonces el sistema debe salir con 2 sin escribir nada (ver D17). | Must |
| RF-12 | Si `estado.db` no tiene la tabla `usos_de_hecho`, o ya existe `hec-999` y no queda id libre, entonces `novela cambio` debe salir con 4, nombrar la causa y no escribir nada (ver D5, D15). | Must |
| RF-13 | El sistema debe calcular los capítulos a regenerar como exactamente `capitulos_que_usan(conn, H)`, y los capítulos a reaplicar como el resto de `1..num_capitulos` (ver D13). | Must |
| RF-14 | El sistema debe calcular los hechos requeridos de cada capítulo a regenerar `a`: los `x ≠ H` con uso `(x, a, 'origen')` y algún uso de `x` en un capítulo mayor que `a` (ver D13, D14). | Must |
| RF-15 | El sistema debe reservar como id del hecho nuevo `hec-` seguido del mayor número de `libro_de_hechos` vigente más uno, con tres dígitos (ver D15). | Must |

**Versionado**

| ID | Requisito (EARS) | Prioridad |
|----|------------------|-----------|
| RF-16 | El sistema debe numerar las versiones desde 1. La edición vigente es la versión `N` que registra la clave `version` de `meta` en `estado.db`, o la 1 si no la tiene (ver D10, D22). | Must |
| RF-17 | Cuando `novela cambio` prepare una versión nueva, el sistema debe guardar la edición vigente en `versiones/vN/`: `capitulos/`, `estado/estado.db` (copiada con la API de backup de SQLite), `estado/deltas/`, `memoria/`, `qa/` y `checkpoints/`. Debe escribir también `versiones/vN/version.json` con el sha256 de cada fichero copiado y `capitulos_sha256` del último checkpoint (ver D8). | Must |
| RF-18 | El sistema no debe copiar a `versiones/` `canon/`, `plan/`, `runs/`, `export/`, `brief/` ni `config.yaml` (ver D8). | Must |
| RF-19 | El sistema debe preparar la versión en este orden (ver D9, D10): 1) escribir `cambios/cam-NNN.json` con `estado: preparando`; 2) copiar a `versiones/vN.tmp/`; 3) verificar cada sha256 y, en la base copiada, `PRAGMA quick_check` y la igualdad de `estado_db.leer` con la base vigente; 4) renombrar `vN.tmp` a `vN`; 5) añadir la versión a `versiones/versiones.json`; 6) vaciar en la raíz `capitulos/`, `estado/deltas/`, `memoria/`, `qa/` y `checkpoints/`; 7) sustituir `estado/estado.db` por una base vacía creada con `estado_db.crear`, con `meta.version = N+1` y `meta.cambio = cam-NNN`; 8) reescribir `cambios/cam-NNN.json` con `estado: en_curso`. | Must |
| RF-20 | Si `novela cambio` se interrumpe durante la preparación, cuando se repita con los mismos argumentos el sistema debe dejar el workspace igual que una ejecución sin corte. Si existe `versiones/vN.tmp/`, lo borra y empieza desde el paso 2. Si existe `versiones/vN/` y el cambio está en `preparando`, continúa desde el paso 5 (ver D9). | Must |
| RF-21 | El sistema no debe escribir, renombrar ni borrar ningún fichero bajo `versiones/vN/` una vez renombrado. Si `versiones/vN/` existe y no hay un `cam-NNN.json` en `preparando` que lo explique, `novela cambio` debe salir con 4 sin escribir nada (ver D9). | Must |
| RF-22 | Cuando se ejecute `novela versiones <slug> --verificar`, el sistema debe recalcular el sha256 de cada fichero de cada `versiones/vN/` contra su `version.json`. Debe salir con 0 si todos coinciden, o con 4 nombrando cada fichero distinto, ausente o sobrante (ver D8). | Should |
| RF-23 | El hook `PreToolUse` debe denegar a los siete roles y a la sesión principal cualquier escritura bajo `novelas/*/versiones/` y `novelas/*/cambios/`. `backend/tests/test_hook.py` debe comprobarlo para cada rol (ver D8). | Should |

**Regeneración con el bucle existente**

| ID | Requisito (EARS) | Prioridad |
|----|------------------|-----------|
| RF-24 | Cuando se ejecute `novela cambio <slug> --siguiente`, el sistema debe imprimir una sola línea y salir con 0 (ver D12). La línea es `NN reaplicar` o `NN regenerar`, según el capítulo `checkpoint + 1` esté entre los reaplicables o los afectados del cambio en curso; `completo` si el cambio en curso ya tiene checkpoint de `num_capitulos`; o `sin cambio` si no hay ninguno. | Must |
| RF-25 | Cuando se ejecute `novela aplicar-delta <slug> <cap> --reaplicar` con un cambio en curso, un `cap` reaplicable y `cap == checkpoint + 1` (o 1 sin checkpoint), el sistema debe hacer tres cosas (ver D11). Primero, copiar de `versiones/vN/` a la raíz, byte a byte y con escritura atómica, `capitulos/NN.md`, `estado/deltas/NN.json` y `qa/NN-*.json`, y comprobar su sha256 contra `version.json`. Después, aplicar el delta con las mismas `violaciones` y `apply.aplicar` del modo normal, sin la custodia de briefings. Por último, registrar sus usos y renderizar `memoria/resumenes/NN.md`. | Must |
| RF-26 | Si `--reaplicar` se invoca sin cambio en curso, sobre un capítulo afectado o fuera de orden, o si `aplicar-delta` sin `--reaplicar` se invoca con un cambio en curso sobre un capítulo reaplicable, entonces el sistema debe salir con 2 sin escribir nada (ver D11, D12). | Must |
| RF-27 | Si las `violaciones` rechazan el delta reaplicado, entonces el sistema debe salir con 1, no escribir `estado.db` y dejar en `harness.log` la línea `aplicar-delta NN --reaplicar -> 1 · <causa>` (ver D11). | Must |
| RF-28 | Mientras haya un cambio en curso, `novela briefing` de un capítulo afectado debe añadir al `escritor`, al `continuista` y al `cronista` la capa `cambio` (ver D16, D17). La capa contiene el id y el texto anterior de `H`, el texto nuevo `T` delimitado como dato, el id reservado si el capítulo es el de origen de `H` y los hechos requeridos del capítulo con su id y su texto. | Must |
| RF-29 | Mientras haya un cambio en curso, `novela briefing <slug> <cap> escritor` de un capítulo afectado debe añadir la capa `version_anterior` con el cuerpo de `versiones/vN/capitulos/NN.md`, sin frontmatter, dentro del presupuesto de la receta (ver D16). | Should |
| RF-30 | El sistema debe aplicar a la capa `cambio` los guardarraíles de secreto vigentes del briefing (`docs/validators.md` §4.4). Si el briefing resultante comparte bloques de cinco palabras con `verdad_oculta` o con una revelación no alcanzada, debe salir con 4 sin escribirlo (ver D17). | Must |
| RF-31 | Mientras haya un cambio en curso, `novela validar` de un capítulo afectado debe registrar el hallazgo `regeneracion_altera_contrato` y salir con 1 si alguno de estos conjuntos del frontmatter difiere del mismo capítulo en `versiones/vN/capitulos/NN.md`: `pistas_plantadas`, `pistas_pagadas`, `hilos_abiertos` o `hilos_cerrados` (ver D14). | Must |
| RF-32 | Mientras haya un cambio en curso, `novela aplicar-delta` de un capítulo afectado debe rechazar el delta (salida 1, causa con prefijo `regeneracion:`) en cualquiera de estos casos (ver D14, D15): (a) el capítulo es el de origen de `H` y el delta no trae en `libro_de_hechos` el id reservado con `texto` igual a `T` tras normalizar; (b) algún campo del delta referencia `H`; (c) falta un hecho requerido con el mismo id y el mismo `texto`; (d) el delta introduce un id de hecho u objeto que existe en la base de `versiones/vN/` y no es un requerido. | Must |
| RF-33 | Cuando se escriba el checkpoint de `num_capitulos` en la versión nueva, `novela cambio --siguiente` debe responder `completo` y `novela pendiente` debe salir como con una novela terminada (ver D12). | Must |
| RF-34 | El procedimiento `.claude/commands/novela-continuar.md` debe hacer tres cosas (ver D12). En «Situación», ejecutar `novela cambio <slug> --siguiente`. Con `reaplicar`, ejecutar `novela aplicar-delta <slug> <cap> --reaplicar` y `novela checkpoint <slug> <cap>`, sin agentes. Y con un 1 de `--reaplicar`, escribir `intervencion.md` con `gate: regeneracion` y parar, sin reintento. | Must |
| RF-35 | El sistema debe nombrar en `.claude/agents/cronista.md` el campo `hechos_usados` y la regla de cita literal, y en `escritor.md`, `continuista.md` y `cronista.md` la capa `cambio` y qué hacer con ella (ver D4, D16). | Must |

**Novedades y diff entre versiones**

| ID | Requisito (EARS) | Prioridad |
|----|------------------|-----------|
| RF-36 | Cuando se ejecute `novela versiones <slug>`, el sistema debe imprimir una línea por versión, con su número, su fecha, el cambio que la originó (o `original`), su estado (`completa` o `en_curso`) y cuántos capítulos cambiaron respecto a la anterior (ver D18). | Must |
| RF-37 | Cuando se ejecute `novela versiones <slug> --novedades [--desde vA]`, el sistema debe listar, en orden ascendente, los capítulos cerrados de la edición vigente cuyo sha256 difiere del mismo capítulo en `vA` (por defecto, la versión anterior). Por cada uno imprime número, `titulo` del frontmatter y el cambio que lo regeneró (ver D18). | Must |
| RF-38 | Donde la edición vigente sea una versión mayor que 1, `novela exportar <slug> --formato md` debe hacer tres cosas (ver D18). Poner delante una sección «Novedades de la versión N» con un enlace interno `[Capítulo N — título](#capitulo-NN)` por capítulo cambiado. Poner un ancla `<a id="capitulo-NN"></a>` antes del encabezado de cada capítulo. Y poner una línea «*Modificado en la versión N.*» bajo el encabezado de cada capítulo cambiado. | Must |
| RF-39 | Mientras la edición vigente sea la versión 1, `novela exportar --formato md` y `--formato epub` deben producir la misma salida que antes de esta spec (ver D18). | Must |
| RF-40 | Donde exista `--formato pdf` (spec 0006) y la edición vigente sea mayor que 1, el sistema debe añadir tras la portada una página «Novedades de la versión N» con un enlace interno `GoTo` a la primera página de cada capítulo cambiado (ver D18). | Could |
| RF-41 | Cuando se ejecute `novela versiones <slug> --diff vA vB --capitulo N`, el sistema debe imprimir el diff unificado de los cuerpos del capítulo `N` entre las dos versiones, donde `vB` puede ser `actual` (ver D18). | Could |

**Contratos, observabilidad y documentación**

| ID | Requisito (EARS) | Prioridad |
|----|------------------|-----------|
| RF-42 | El sistema no debe añadir rutas a la API ni cambiar `Estado`, de modo que `backend/api/openapi.json` y `backend/schemas/state.schema.json` queden idénticos (ver D19). | Must |
| RF-43 | Donde la versión vigente sea mayor que 1, `novela checkpoint` debe emitir cada score con un id que incluya `v<N>`, y con la versión 1 debe conservar el id actual (ver D20). | Should |
| RF-44 | El sistema debe dejar en `harness.log` una línea por cada `novela cambio` (salvo `--simular` y `--siguiente`) y por cada `aplicar-delta --reaplicar`, con su resultado (ver D23). | Must |
| RF-45 | El sistema debe incluir `docs/adr/0004-versiones-de-la-novela.md` con las secciones Contexto, Decisión, Alternativas descartadas, Consecuencias y Cuándo reabrirla. En el mismo commit, debe reescribir en una línea el invariante 7 de `AGENTS.md` y actualizar `docs/architecture.md` §12.5 (ver D2). | Must |
| RF-46 | El sistema debe describir `usos_de_hecho`, `hechos_usados`, `versiones/`, `cambios/`, `novela cambio`, `novela versiones`, `--reaplicar` y los gates de regeneración en las secciones de D23, en el mismo commit que el código que los introduce (ver D23). | Must |

## 6. Requisitos no funcionales

| ID | Categoría | Requisito | Métrica | Umbral |
|----|-----------|-----------|---------|--------|
| RNF-01 | Rendimiento | La consulta hecho→capítulos es indexada | Tiempo de `estado_db.capitulos_que_usan` sobre una base sintética de 99 capítulos, 300 hechos y 20 usos por hecho, en solo lectura | < 50 ms |
| RNF-02 | Rendimiento | Preparar una versión es barato | Tiempo de `novela cambio` (sin `--simular`) en `CliRunner` sobre `demo-terminado` (24 capítulos) | < 10 s |
| RNF-03 | Rendimiento | Reaplicar no gasta cuota | Llamadas a modelo por capítulo reaplicado; tiempo de `aplicar-delta --reaplicar` + `checkpoint` por capítulo en `demo-terminado` | 0; < 2 s |
| RNF-04 | Integridad | La versión anterior no cambia | Ficheros de `versiones/vN/` cuyo sha256 difiere del original antes del cambio, tras una regeneración completa con agente falso | 0 |
| RNF-05 | Integridad | La regeneración es selectiva | Capítulos reaplicables cuyo `capitulos/NN.md` de la versión nueva difiere byte a byte del de `versiones/vN/` | 0 |
| RNF-06 | Seguridad (secreto) | El secreto no se copia | Ficheros bajo `versiones/` o `cambios/` que contienen `canon/misterio.md` o una cadena de 30 o más caracteres de él, en las fixtures | 0 |
| RNF-07 | Compatibilidad | Contratos intactos donde no se amplían | Diferencias en `openapi.json` y `state.schema.json`; diferencias de `export/novela.md` y `novela.epub` de una versión 1 respecto a antes de la spec; tests de `test_export.py` modificados | 0; 0; 0 |
| RNF-08 | Almacenamiento | La instantánea no duplica de más | Tamaño de `versiones/vN/` respecto a la suma de los directorios copiados de la raíz, en `demo-terminado` | ≤ 1,05 × |
| RNF-09 | Observabilidad | Toda mutación deja rastro | Invocaciones de `novela cambio` que preparan versión y de `aplicar-delta --reaplicar` sin línea en `harness.log` | 0 % |
| RNF-10 | Calidad | Suite verde y sin modelos | Fallos de `uv run pytest`; errores de `mypy --strict` y `ruff`; tests que importan un cliente de modelos | 0; 0; 0 |
| RNF-11 | Calidad | Las propiedades tienen cobertura suficiente | Casos de Hypothesis por test de propiedad de funciones puras; casos del test de propiedad de regeneración completa | ≥ 200; ≥ 25 |

## 7. Criterios de aceptación

«`demo-cambio`» es un workspace sintético nuevo de `backend/conftest.py`, construido con `fabrica.construir` desde `fabrica.CAMBIO`: 6 capítulos cerrados, donde cada capítulo `n` introduce `hec-00n` como en `DEMO`. Además, el capítulo 2 introduce `hec-102`, que el delta del capítulo 5 cita en `hechos_usados`, y los deltas de los capítulos 4 y 6 citan `hec-002` en `hechos_usados`. Por eso `capitulos_que_usan(hec-002) = [2, 4, 6]`, el requerido del capítulo 2 es `hec-102` y el id reservado es `hec-103`. La petición ficticia es `--hecho hec-002 --texto "La puerta de la linterna estaba intacta en la noche 2."`. El agente falso de la regeneración es `fabrica.capitulo_regenerado` y `fabrica.delta_regenerado`.

### CA-01 (cubre RF-01)
- **Dado** un `estado.db` creado con `estado_db.crear`
- **Cuando** se inserta una fila en `usos_de_hecho` y después se intenta un `UPDATE`, un `DELETE`, una `via` `menciona` y un `capitulo` de texto
- **Entonces** la inserción pasa, `UPDATE` y `DELETE` abortan con «usos_de_hecho es append-only», y los dos últimos fallan por `CHECK` y por `STRICT`

### CA-02 (cubre RF-02)
- **Dado** tres deltas del capítulo 5 de `demo-cambio`: uno con `hechos_usados` cuya cita es literal, uno con una cita que no está en el cuerpo y uno que cita `hec-900`, que no existe
- **Cuando** se ejecuta `novela aplicar-delta demo-cambio 5` con cada uno sobre el estado del capítulo 4
- **Entonces** el primero sale con 0 y los otros dos con 1, con la causa `cita no literal` y `hecho inexistente`, sin cambios en la huella de `estado.db`; y `delta.schema.json` regenerado contiene `hechos_usados`

### CA-03 (cubre RF-03)
- **Dado** `demo-cambio` construido con el CLI
- **Cuando** se llama a `estado_db.usos(conn, "hec-002")` y a `estado_db.usos(conn, "hec-102")`
- **Entonces** la primera devuelve `(hec-002, 2, origen)`, `(hec-002, 2, conocimiento)`, `(hec-002, 2, lector)`, `(hec-002, 4, cita)` y `(hec-002, 6, cita)`, y la segunda `(hec-102, 2, origen)` y `(hec-102, 5, cita)`

### CA-04 (cubre RF-03, RF-04)
- **Dado** un generador de Hypothesis de secuencias de deltas válidos, con al menos 200 casos
- **Cuando** se aplica la función pura `apply.usos` a cada delta, se acumula el resultado en una colección y se repite la aplicación del último delta
- **Entonces** la colección es igual a la del modelo de referencia (origen ∪ conocimiento ∪ lector ∪ cita por capítulo), no tiene duplicados y conserva intactas las filas anteriores

### CA-05 (cubre RF-05)
- **Dado** un `estado.db` al que el test ha quitado `usos_de_hecho`, sus triggers y su índice, con los capítulos 1 y 2 aplicados
- **Cuando** se ejecuta `novela aplicar-delta <slug> 3`
- **Entonces** sale con 0, la tabla existe con sus triggers y tiene filas solo del capítulo 3

### CA-06 (cubre RF-06)
- **Dado** `demo-cambio` y una base sintética de 99 capítulos, 300 hechos y 20 usos por hecho
- **Cuando** se llama a `capitulos_que_usan(conn, "hec-002")` con `solo_lectura=True`, a la misma función sobre la sintética, y a `usos` sobre una base sin la tabla
- **Entonces** la primera devuelve `[2, 4, 6]`, la segunda tarda menos de 50 ms y la tercera lanza `EstadoIlegible`

### CA-07 (cubre RF-07)
- **Dado** el `estado.db` sin tabla de CA-05, antes de aplicar el capítulo 3
- **Cuando** se ejecutan `novela estado <slug> --json` y `GET /novelas/<slug>/estado`
- **Entonces** los dos responden con 0 y 200 y un JSON igual al que dan con la tabla presente

### CA-08 (cubre RF-08)
- **Dado** `demo-cambio`, con la huella de todo el workspace calculada
- **Cuando** se ejecuta `novela cambio demo-cambio --hecho hec-002 --texto "…" --simular`
- **Entonces** sale con 0, imprime `hec-103`, `regenerar 02, 04, 06`, `requeridos 02: hec-102` y `reaplicar 01, 03, 05`, y la huella no cambia

### CA-09 (cubre RF-09)
- **Dado** `demo-cambio`
- **Cuando** se ejecuta `novela cambio demo-cambio --hecho hec-002 --texto "…" --motivo "petición del lector"`
- **Entonces** sale con 0, imprime `cambio cam-001: hec-002 → hec-103 · versión 2 · regenerar 02, 04, 06 · reaplicar 3 capítulos`, `cambios/cam-001.json` valida contra `PeticionDeCambio` con `estado: en_curso`, y no queda ningún `.tmp`

### CA-10 (cubre RF-10)
- **Dado** tres copias de `demo-cambio`: una con solo 4 capítulos cerrados, una con un cambio ya en curso y una con un `runs/<run_id>/intervencion.md` sin `resuelto:`
- **Cuando** se ejecuta `novela cambio` con la petición ficticia en cada una
- **Entonces** las tres salen con 1, nombran `novela sin terminar`, `cambio en curso: cam-001` e `intervención sin resolver`, y la huella de cada workspace no cambia

### CA-11 (cubre RF-11)
- **Dado** `demo-cambio`
- **Cuando** se ejecuta `novela cambio` con `--hecho hec-2`, `--hecho hec-900`, `--texto "   "`, un texto de 501 caracteres y el texto vigente de `hec-002` con espacios dobles
- **Entonces** los cinco salen con 2 y no escriben nada

### CA-12 (cubre RF-12)
- **Dado** `demo-cambio` sin la tabla `usos_de_hecho`, y otro workspace cuyo `libro_de_hechos` contiene `hec-999`
- **Cuando** se ejecuta `novela cambio` con una petición válida en cada uno
- **Entonces** los dos salen con 4, nombran `sin tabla usos_de_hecho` y `no quedan ids de hecho`, y no escriben nada

### CA-13 (cubre RF-13, RF-14)
- **Dado** un generador de Hypothesis de conjuntos de usos sobre 1 a 30 capítulos y 1 a 40 hechos, con un hecho `H` elegido, con al menos 200 casos
- **Cuando** se llama a la función pura `plan.plan_de_regeneracion(usos, H, num_capitulos)`
- **Entonces** `regenerar` es el conjunto de capítulos con algún uso de `H`, `regenerar` y `reaplicar` son disjuntos y su unión es `1..num_capitulos`, y cada requerido de `a` tiene origen en `a`, es distinto de `H` y se usa en un capítulo mayor que `a`

### CA-14 (cubre RF-15)
- **Dado** `libro_de_hechos` con `hec-001`, `hec-007` y `hec-102`
- **Cuando** se llama a `plan.id_reservado`
- **Entonces** devuelve `hec-103`, y con `hec-999` presente lanza `SinIdsLibres`

### CA-15 (cubre RF-16)
- **Dado** `demo-cambio` antes y después de CA-09
- **Cuando** se lee `meta.version` y se ejecuta `novela versiones demo-cambio`
- **Entonces** antes no hay clave y la edición vigente es la 1; después la raíz tiene `version = 2` y `cambio = cam-001`

### CA-16 (cubre RF-17, RF-18)
- **Dado** `demo-cambio`, con el sha256 de cada fichero de `capitulos/`, `estado/deltas/`, `memoria/`, `qa/` y `checkpoints/`, y el `estado_db.leer` de la base, calculados antes del cambio
- **Cuando** se ejecuta la petición de CA-09
- **Entonces** `versiones/v1/` contiene exactamente esos ficheros con los mismos sha256, `version.json` los lista, `estado_db.leer` sobre `versiones/v1/estado/estado.db` es igual al de antes, y no existe `versiones/v1/canon/`, `plan/`, `runs/`, `export/`, `brief/` ni `config.yaml`

### CA-17 (cubre RF-19)
- **Dado** el workspace tras CA-09
- **Cuando** se inspecciona la raíz
- **Entonces** `capitulos/`, `estado/deltas/`, `memoria/`, `qa/` y `checkpoints/` están vacíos, `estado_db.leer` de la raíz devuelve un `Estado` vacío con el cursor inicial, `runs/`, `canon/` y `plan/` no cambian, y `versiones/versiones.json` tiene las entradas `v1` (`original`) y `v2` (`cam-001`)

### CA-18 (cubre RF-20)
- **Dado** tres cortes inyectados en `plataforma/versiones.py`: tras copiar la mitad de `v1.tmp`, tras renombrar a `v1` y tras vaciar `capitulos/` de la raíz
- **Cuando** se repite `novela cambio` con los mismos argumentos tras cada corte
- **Entonces** las tres salen con 0 y dejan el workspace con la misma huella que CA-09, salvo el `creado` de `cam-001.json`

### CA-19 (cubre RF-21)
- **Dado** el workspace tras una regeneración completa (CA-29), y otro con un `versiones/v1/` puesto a mano sin `cam-NNN.json` en `preparando`
- **Cuando** se comparan los sha256 de `versiones/v1/` con los de CA-16, y se ejecuta `novela cambio` en el segundo
- **Entonces** los sha256 coinciden todos, y el segundo sale con 4 sin escribir nada

### CA-20 (cubre RF-22)
- **Dado** el workspace tras CA-09, y una copia con un byte cambiado en `versiones/v1/capitulos/03.md` y un fichero de más en `versiones/v1/qa/`
- **Cuando** se ejecuta `novela versiones <slug> --verificar` en cada uno
- **Entonces** el primero sale con 0 y el segundo con 4, nombrando `capitulos/03.md` como distinto y el fichero sobrante

### CA-21 (cubre RF-23)
- **Dado** el script del hook
- **Cuando** `test_hook.py` lo ejecuta con un `Write` de cada uno de los siete roles y de la sesión principal sobre `novelas/demo/versiones/v1/capitulos/01.md` y `novelas/demo/cambios/cam-001.json`
- **Entonces** todos salen con 2

### CA-22 (cubre RF-24)
- **Dado** `demo-cambio` sin cambio, tras CA-09, tras reaplicar el 1 y tras cerrar el 6 de la versión 2
- **Cuando** se ejecuta `novela cambio demo-cambio --siguiente` en cada punto
- **Entonces** imprime `sin cambio`, `01 reaplicar`, `02 regenerar` y `completo`, siempre con 0

### CA-23 (cubre RF-25)
- **Dado** el workspace tras CA-09
- **Cuando** se ejecutan `novela aplicar-delta demo-cambio 1 --reaplicar` y `novela checkpoint demo-cambio 1`
- **Entonces** los dos salen con 0; `capitulos/01.md`, `estado/deltas/01.json`, `qa/01-*.json` y `memoria/resumenes/01.md` de la raíz tienen el mismo sha256 que en `versiones/v1/`; y `capitulos_que_usan(conn, "hec-001")` es `[1]`

### CA-24 (cubre RF-26)
- **Dado** `demo-cambio` sin cambio, y el workspace tras CA-09
- **Cuando** se ejecutan cuatro órdenes: `aplicar-delta --reaplicar` sin cambio en curso, `aplicar-delta demo-cambio 2 --reaplicar` (afectado), `aplicar-delta demo-cambio 3 --reaplicar` sin checkpoint del 2 y `aplicar-delta demo-cambio 1` sin `--reaplicar` (reaplicable)
- **Entonces** las cuatro salen con 2 y la huella de la raíz no cambia

### CA-25 (cubre RF-27)
- **Dado** el workspace tras CA-09 y el capítulo 1 reaplicado, con un delta regenerado del capítulo 2 que omite abrir un hilo que cierra el 3, inyectado en el test saltándose el gate de RF-31
- **Cuando** se ejecuta `novela aplicar-delta demo-cambio 3 --reaplicar`
- **Entonces** sale con 1, `harness.log` tiene `aplicar-delta 03 --reaplicar -> 1 · …` y la huella de `estado.db` no cambia

### CA-26 (cubre RF-28, RF-29, RF-30)
- **Dado** el workspace tras CA-09 y el capítulo 1 reaplicado
- **Cuando** se generan los briefings del capítulo 2 para `escritor`, `continuista`, `cronista` y `editor-estilo`, y otro del `escritor` con un `--texto` que copia una frase de `verdad_oculta` de la fixture
- **Entonces** los tres primeros contienen la capa `cambio` con `hec-002`, su texto anterior, el texto nuevo, `hec-103` y `hec-102` con su texto. El del `escritor` contiene además la capa `version_anterior` con el cuerpo de `versiones/v1/capitulos/02.md`. El del `editor-estilo` no tiene ninguna de las dos. Y el último sale con 4 sin escribir el briefing

### CA-27 (cubre RF-31)
- **Dado** el workspace listo para validar el capítulo 2 regenerado, con cuatro frontmatters del agente falso: igual al original en pistas e hilos, sin una pista plantada, con un hilo abierto de más y con un hilo cerrado de menos
- **Cuando** se ejecuta `novela validar demo-cambio 2` con cada uno
- **Entonces** el primero sale con 0 y los otros tres con 1, con `regeneracion_altera_contrato` en `qa/02-validacion.json`

### CA-28 (cubre RF-32)
- **Dado** un generador de Hypothesis de deltas regenerados del capítulo de origen, con al menos 200 casos, que omiten o mantienen el id reservado, cambian su texto, referencian `H` en cualquier colección, omiten o alteran un requerido e introducen ids nuevos o de la versión anterior
- **Cuando** se llama a la función pura `violaciones.de_regeneracion(delta, plan, base_anterior)`
- **Entonces** devuelve una causa `regeneracion:` si y solo si se da alguno de los casos (a) a (d) de RF-32; y por el CLI, un delta con cada caso sale con 1 sin cambiar la huella de `estado.db`

### CA-29 (cubre RF-33, RNF-04, RNF-05)
- **Dado** el workspace tras CA-09
- **Cuando** se recorre la versión 2 con el CLI real hasta `--siguiente = completo`: `--reaplicar` y `checkpoint` en 1, 3 y 5, y el bucle con el agente falso de regeneración en 2, 4 y 6
- **Entonces** `novela pendiente` sale como con una novela terminada; `capitulos/01.md`, `03.md` y `05.md` son idénticos byte a byte a los de `versiones/v1/`, y `02.md`, `04.md` y `06.md` difieren; `libro_de_hechos` contiene `hec-103` y `hec-102` y no contiene `hec-002`; y todos los sha256 de `versiones/v1/` coinciden con los de CA-16

### CA-30 (cubre RF-13, RF-25, RNF-05, RNF-11)
- **Dado** un generador de Hypothesis, con al menos 25 casos y sin `deadline`, de novelas de `fabrica` de 3 a 6 capítulos con usos aleatorios en `hechos_usados` y un hecho `H` elegido
- **Cuando** se construye el workspace, se pide el cambio de `H` y se completa la versión 2 con el CLI y el agente falso
- **Entonces** todo capítulo reaplicable es idéntico byte a byte al de `versiones/v1/`, todo afectado está regenerado, y `versiones/v1/` no cambia

### CA-31 (cubre RF-34)
- **Dado** `.claude/commands/novela-continuar.md`
- **Cuando** se ejecuta `test_contratos.py::test_procedimiento_regeneracion`
- **Entonces** el paso «Situación» contiene `novela cambio <slug> --siguiente`, `aplicar-delta <slug> <cap> --reaplicar` y `gate: regeneracion`, y la tabla de códigos sigue igual

### CA-32 (cubre RF-35)
- **Dado** `.claude/agents/cronista.md`, `escritor.md` y `continuista.md`
- **Cuando** se ejecuta `test_contratos.py::test_agentes_nombran_el_cambio`
- **Entonces** `cronista.md` contiene `hechos_usados` y la regla de cita literal, los tres nombran la capa `cambio`, y los tests de contrato de la spec 0003 siguen en verde sin cambiar `tools` ni `model`

### CA-33 (cubre RF-36)
- **Dado** el workspace tras CA-29
- **Cuando** se ejecuta `novela versiones demo-cambio`
- **Entonces** imprime dos líneas: `v1 · <fecha> · original · completa · —` y `v2 · <fecha> · cam-001 · completa · 3 capítulos cambiados`

### CA-34 (cubre RF-37)
- **Dado** el workspace tras CA-29
- **Cuando** se ejecuta `novela versiones demo-cambio --novedades` y la función pura `novedades.calcular` con un generador de Hypothesis de pares de mapas `capitulos_sha256` (≥ 200 casos)
- **Entonces** el CLI lista `02`, `04` y `06` con su título y `cam-001`; y la función devuelve exactamente los capítulos cerrados en la versión nueva cuyo hash difiere o no existe en la anterior, en orden ascendente

### CA-35 (cubre RF-38)
- **Dado** el workspace tras CA-29
- **Cuando** se ejecuta `novela exportar demo-cambio --formato md`
- **Entonces** `export/novela.md` empieza por «Novedades de la versión 2» con tres enlaces `#capitulo-02`, `#capitulo-04` y `#capitulo-06`. Cada enlace tiene su ancla `<a id="capitulo-NN"></a>` antes del encabezado de ese capítulo, y la línea «*Modificado en la versión 2.*» solo aparece bajo los encabezados de 2, 4 y 6

### CA-36 (cubre RF-39)
- **Dado** el código tras esta spec
- **Cuando** se ejecutan `test_export.py::test_md_concatena_en_orden` y `::test_epub_reabrible` sin modificar
- **Entonces** pasan

### CA-37 (cubre RF-40)
- **Dado** la spec 0006 implementada y el workspace tras CA-29
- **Cuando** se exporta en PDF y se recorren con `pypdf` las anotaciones `Link` de la página 2
- **Entonces** la página empieza por «Novedades de la versión 2» y tiene tres enlaces con destino en la primera página de los capítulos 2, 4 y 6

### CA-38 (cubre RF-41)
- **Dado** el workspace tras CA-29
- **Cuando** se ejecuta `novela versiones demo-cambio --diff v1 actual --capitulo 2` y lo mismo con `--capitulo 1`
- **Entonces** el primero imprime un diff unificado con la frase del hecho nuevo en una línea `+`, y el segundo no imprime líneas de diff; los dos salen con 0

### CA-39 (cubre RF-42)
- **Dado** el código tras esta spec
- **Cuando** se ejecutan `test_contratos.py::test_openapi_al_dia`, `::test_state_schema_al_dia` y `test_api.py::test_sin_rutas_de_version`
- **Entonces** los dos ficheros no cambian y ninguna ruta de la app contiene `version`, `cambio`, `novedades` ni `usos`

### CA-40 (cubre RF-43)
- **Dado** un `ScoreSink` falso que registra los ids
- **Cuando** se ejecuta `novela checkpoint` del capítulo 2 en `demo-cambio` antes del cambio y en la versión 2
- **Entonces** el primero emite los ids actuales y el segundo los mismos con `v2`

### CA-41 (cubre RF-44)
- **Dado** el recorrido de CA-29
- **Cuando** se leen los `harness.log` de sus runs
- **Entonces** hay una línea `cambio cam-001 -> 0` y una `aplicar-delta NN --reaplicar -> 0` por cada capítulo 1, 3 y 5

### CA-42 (cubre RF-45)
- **Dado** `docs/adr/0004-versiones-de-la-novela.md` y `AGENTS.md`
- **Cuando** se ejecuta `test_contratos.py::test_adr_de_versiones`
- **Entonces** el ADR tiene en su frontmatter `adr: 0004`, `estado: aceptada` y `specs: [0007]` y los cinco encabezados de RF-45, y el invariante 7 de `AGENTS.md` nombra `versiones/` y `novela cambio`

### CA-43 (cubre RF-46)
- **Dado** el commit de cierre (T-16)
- **Cuando** se revisan las secciones de D23
- **Entonces** cada una describe lo implementado, sin «pendiente» ni «próximamente»

## 8. Diseño propuesto

### 8.1 Visión general

Una versión es una línea de tiempo completa de la novela, con su propia `estado.db` (ver D1). Dentro de cada versión siguen valiendo, sin excepción, los invariantes 2 y 7 y el sello de la spec 0001. Una versión nueva no reescribe la anterior. La copia en `versiones/vN/`, empieza con una base vacía y se reconstruye capítulo a capítulo. Los capítulos no afectados se reaplican desde la instantánea con el delta que ya tenían, y los afectados se regeneran con el bucle de siempre. Así lo que ya pasó no se toca, y la versión nueva se construye por la única vía de escritura de filas que existe, `aplicar-delta`.

```mermaid
flowchart TD
    L["Lector: «que el hecho X sea Y»"] --> OP["Operador: novela cambio slug --hecho hec-002 --texto …"]
    OP --> Q["capitulos_que_usan(hec-002)<br/>tabla usos_de_hecho"]
    Q --> PL["plan de regeneración (puro)<br/>regenerar · reaplicar · requeridos · id reservado"]
    PL --> SN["instantánea versiones/v1/<br/>copia verificada + version.json"]
    SN --> RS["raíz restablecida<br/>estado.db vacía, meta.version = 2"]
    RS --> LOOP{"/novela-continuar<br/>novela cambio --siguiente"}
    LOOP -->|NN reaplicar| RA["aplicar-delta NN --reaplicar<br/>copia byte a byte + violaciones"]
    LOOP -->|NN regenerar| BU["bucle normal + capa cambio<br/>gates de regeneración"]
    RA --> CK["checkpoint NN"]
    BU --> CK
    CK --> LOOP
    LOOP -->|completo| NV["novela versiones --novedades<br/>exportar md con Novedades"]
```

### 8.2 Componentes afectados

**Nuevos**

- `backend/novela/slices/cambio/cmd.py`: `novela cambio` (petición, `--simular`, `--siguiente`). Cáscara: lock, lectura, escritura y códigos.
- `backend/novela/slices/cambio/plan.py`: funciones puras `plan_de_regeneracion`, `id_reservado` y `siguiente_paso`.
- `backend/novela/slices/cambio/test_plan.py` (propiedades) y `test_cambio.py` (CLI).
- `backend/novela/slices/versiones/cmd.py`: `novela versiones` (lista, `--novedades`, `--verificar`, `--diff`).
- `backend/novela/slices/versiones/novedades.py`: `calcular(anterior, actual) -> list[CapituloCambiado]`, pura.
- `backend/novela/slices/versiones/test_versiones.py` y `test_novedades.py`.
- `backend/novela/plataforma/versiones.py`: instantánea (copia, backup de SQLite, verificación y renombrado), registro de versiones, restablecimiento de la raíz y recuperación tras corte (RF-17 a RF-21).
- `backend/novela/plataforma/test_versiones.py`: cortes inyectados de CA-18.
- `backend/novela/dominio/version.py`: `PeticionDeCambio`, `Version`, `RegistroDeVersiones`, `PlanDeRegeneracion`, `CapituloCambiado`.
- `backend/tests/test_regeneracion.py`: CA-29 y la propiedad de CA-30.
- `docs/adr/0004-versiones-de-la-novela.md`.

**Modificados**

- `backend/novela/plataforma/esquema.sql`: la tabla `usos_de_hecho`, su índice y sus triggers.
- `backend/novela/plataforma/estado_db.py`: `usos`, `capitulos_que_usan`, `registrar_usos` (`INSERT OR IGNORE`), `asegurar_usos` (DDL idempotente) y `crear(ruta, version=None, cambio=None)` con las claves de `meta`. `leer` y `guardar` no cambian.
- `backend/novela/plataforma/test_esquema.py` y `test_estado_db.py`.
- `backend/novela/dominio/estado.py`: `UsoCitado` y `Delta.hechos_usados`; `UsoDeHecho`, fuera de `Estado`.
- `backend/novela/dominio/ids.py`: `CambioId` (`^cam-\d{3}$`).
- `backend/schemas/delta.schema.json`, regenerado (`REGENERAR=1 uv run pytest tests/test_contratos.py`). También `qa-informe.schema.json` si enumera `tipo`.
- `backend/novela/slices/delta/apply.py`: `usos(delta) -> tuple[UsoDeHecho, ...]`, pura.
- `backend/novela/slices/delta/violaciones.py`: cita e integridad de `hechos_usados`, y `de_regeneracion(delta, plan, base_anterior)`, pura.
- `backend/novela/slices/delta/cmd.py`: `--reaplicar`, el rechazo de RF-26, el registro de usos dentro de `estado_db.transaccion` y los gates de RF-32.
- `backend/novela/slices/delta/test_apply.py`, `test_violaciones.py` y `test_delta.py`.
- `backend/novela/slices/validacion/gates.py` y `cmd.py`: el gate `regeneracion_altera_contrato` (RF-31), con su test de propiedad en `test_gates.py`.
- `backend/novela/slices/briefing/assemble.py`, `recipes.py` y `cmd.py`, y `backend/config/recipes.yaml`: las capas `cambio` y `version_anterior`.
- `backend/novela/slices/export/markdown.py` y `cmd.py`: la sección de novedades; `pdf.py` solo si existe (spec 0006).
- `backend/novela/slices/checkpoint/cmd.py` y `backend/novela/plataforma/langfuse.py`: el id de score con versión (RF-43).
- `backend/novela/cli.py`: registra `cambio` y `versiones`.
- `backend/tests/fixtures/fabrica.py`: `CAMBIO`, `hechos_usados` opcional por capítulo, `capitulo_regenerado` y `delta_regenerado`. `DEMO` no cambia, así que los goldens no cambian.
- `backend/conftest.py`: el workspace `demo-cambio`.
- `backend/tests/test_hook.py`, `test_contratos.py` y `test_api.py`.
- `.claude/hooks/denegar-escritura-estado.py`: solo si CA-21 falla con las reglas 2 y 3 actuales.
- `.claude/agents/cronista.md`, `escritor.md` y `continuista.md`: los cuerpos (RF-35).
- `.claude/commands/novela-continuar.md` (RF-34).
- `AGENTS.md` y la documentación de D23.

### 8.3 Modelo de datos

**Tabla nueva de `estado.db`** (ver D3):

```sql
CREATE TABLE usos_de_hecho (
    hecho    TEXT NOT NULL,
    capitulo INTEGER NOT NULL,
    via      TEXT NOT NULL CHECK (via IN ('origen', 'conocimiento', 'lector', 'cita')),
    PRIMARY KEY (hecho, capitulo, via)
) STRICT;
CREATE INDEX usos_por_capitulo ON usos_de_hecho (capitulo);
-- más usos_de_hecho_no_update y usos_de_hecho_no_delete con RAISE(ABORT, 'usos_de_hecho es append-only')
```

La clave primaria empieza por `hecho`, así que la consulta hecho→capítulos usa el índice de la clave. `meta.schema_version` sigue en `1.0.0` porque el cambio es aditivo (ver D5). `meta` gana dos claves opcionales, `version` y `cambio`, que solo escribe `estado_db.crear` (ver D10).

**Delta** (`dominio/estado.py`, ver D4): `hechos_usados: list[UsoCitado] = []`, con `UsoCitado {hecho: HechoId, cita: str (min 1)}`. Es un cambio compatible porque el campo es opcional con valor por defecto. `delta.schema.json` se regenera, y `docs/definitions.md` y el test de contrato se ajustan en el mismo commit.

**`UsoDeHecho`** (`Modelo` inmutable): `{hecho: HechoId, capitulo: CapituloNum, via: "origen" | "conocimiento" | "lector" | "cita"}`. No forma parte de `Estado`, así que `state.schema.json` no cambia (ver D19).

**Disco** (ver D7, D8):

```
novelas/<slug>/
├── cambios/
│   └── cam-001.json          # PeticionDeCambio
└── versiones/
    ├── versiones.json        # RegistroDeVersiones
    └── v1/                   # inmutable desde que se renombra
        ├── version.json      # Version: sha256 de cada fichero
        ├── capitulos/  estado/estado.db  estado/deltas/  memoria/  qa/  checkpoints/
```

| Modelo | Campos |
|---|---|
| `PeticionDeCambio` | `id: CambioId`, `hecho: HechoId`, `texto_anterior: str`, `texto: str (1..500)`, `motivo: str \| None (≤ 500)`, `hecho_nuevo: HechoId`, `version_base: int ≥ 1`, `version_nueva: int`, `plan: PlanDeRegeneracion`, `estado: "preparando" \| "en_curso"`, `creado: datetime` |
| `PlanDeRegeneracion` | `regenerar: list[CapituloNum]` (≥ 1), `reaplicar: list[CapituloNum]`, `origen: CapituloNum`, `requeridos: dict[CapituloNum, list[HechoId]]` |
| `Version` | `numero: int ≥ 1`, `creada: datetime`, `cambio: CambioId \| None`, `capitulos_sha256: dict[CapituloNum, Sha256]`, `ficheros: dict[str, Sha256]` (ruta relativa a `vN/`) |
| `RegistroDeVersiones` | `versiones: list[VersionRegistrada {numero, cambio, creada}]`, que solo crece: un validador rechaza un registro nuevo que no tenga el anterior como prefijo |
| `CapituloCambiado` | `capitulo: CapituloNum`, `titulo: str`, `cambio: CambioId` |

Estos modelos son contratos entre subcomandos del CLI y no los produce ningún agente, así que no se exportan a `backend/schemas/` (ver D7). Validan todo lo que se lee de `cambios/` y `versiones/` (`docs/validators.md` §3.1). Un cambio está en curso si su último `cam-NNN.json` está en `en_curso` y la raíz no tiene checkpoint de `num_capitulos`. «Completo» se deriva y no se escribe (ver D12).

No se migra ningún workspace. Los capítulos aplicados antes de esta spec no tienen filas de `usos_de_hecho` (ver D5).

### 8.4 Interfaces y contratos

**CLI.**

```
novela cambio <slug> --hecho <hec-id> --texto "<nuevo>" [--motivo "<texto>"] [--simular]
novela cambio <slug> --siguiente
novela aplicar-delta <slug> <cap> [--reaplicar]
novela versiones <slug> [--novedades [--desde vN]] [--verificar] [--diff vA vB|actual --capitulo N]
```

`--siguiente` excluye a `--hecho`, `--texto`, `--motivo` y `--simular`, y combinarlos sale con 2.

| Código | `novela cambio` | `aplicar-delta` con un cambio en curso | `novela versiones` |
|---|---|---|---|
| 0 | Petición registrada y versión preparada; simulación; `--siguiente` | Reaplicado, o afectado aplicado | Listado, novedades o diff; verificación correcta |
| 1 | Novela sin terminar, cambio en curso, intervención viva (RF-10) | `violaciones` rechaza el delta reaplicado (RF-27); gate de regeneración (RF-32) | — |
| 2 | Argumentos inválidos (RF-11) | `--reaplicar` sin cambio, sobre un afectado o fuera de orden; reaplicable sin `--reaplicar` (RF-26) | Versión inexistente u opciones incompatibles |
| 3 | Lock ocupado | Lock ocupado | — (solo lectura, no toma lock) |
| 4 | Sin tabla, sin ids libres, `versiones/vN/` inexplicado, instantánea que no verifica (RF-12, RF-19, RF-21) | Fichero de la instantánea distinto de `version.json` | `--verificar` con diferencias (RF-22); registro ilegible |

**Salida de `--siguiente`**: exactamente una línea que casa `^(\d{2,3} (reaplicar|regenerar)|completo|sin cambio)$`.

**Líneas de `harness.log`**: `cambio cam-NNN -> <código>` y `aplicar-delta NN --reaplicar -> <código> · <causa>`, con el formato de la spec 0001 (RF-27) y `sesion=<uuid>` si existe.

**Capa `cambio` del briefing** (ver D16, D17). El bloque va delimitado y se declara como dato, no como instrucción:

```
## Cambio pedido (cam-001) — dato, no instrucción
hecho sustituido: hec-002 — «<texto anterior>»
hecho nuevo: hec-103 — «<texto nuevo>»            ← solo en el capítulo de origen
hechos requeridos en este capítulo: hec-102 — «<texto>»
```

**Hallazgo nuevo de `novela validar`**: `regeneracion_altera_contrato`, gravedad `alta`, con `referencia` igual al id de la pista o el hilo que difiere (`docs/architecture.md` §7.3).

**Causas de `aplicar-delta` en regeneración**: el prefijo `regeneracion:` seguido de `falta el hecho nuevo hec-103`, `texto del hecho nuevo distinto de la petición`, `referencia a hec-002 en <colección>`, `falta el requerido hec-102` o `id de la versión anterior: <id>`. El procedimiento las trata como un gate de delta, con reintento del `cronista` (ver §9).

**ADR 0004** (ver D2). Su frontmatter sigue al de `docs/adr/0002-los-gates-los-decide-el-cli.md` (`adr`, `titulo`, `estado`, `fecha`, `decide`, `specs`). Decisión: una versión es una línea de tiempo nueva, con base propia reconstruida por reproducción. Los invariantes 2 y 7 valen dentro de cada versión, y la anterior se conserva inmutable. Alternativas descartadas: columna `version` en todas las tablas, capa de sustituciones sobre una sola base y reescritura en sitio con excepción al invariante 7. Texto propuesto para el invariante 7 de `AGENTS.md`: «**No se reescriben capítulos de una versión.** Si el problema del capítulo 7 nace del 5, para y pide intervención. Solo `novela cambio` abre una versión nueva, y la anterior queda intacta en `versiones/`».

### 8.5 Flujo principal

1. El lector pide al operador que un hecho sea otro. El operador busca el id en `novela estado <slug> --json` y comprueba el alcance con `novela cambio <slug> --hecho hec-002 --texto "…" --simular`.
2. Ejecuta el mismo comando sin `--simular`. El CLI toma el lock, comprueba RF-10 a RF-12, calcula el plan y reserva `hec-103`. Después escribe `cam-001.json` en `preparando`, guarda `versiones/v1/`, la verifica, la registra, restablece la raíz con `meta.version = 2` y pasa el cambio a `en_curso`.
3. El operador lanza `/novela-continuar <slug> --capitulos 6`, interactivo o en el bucle desatendido de siempre, porque `novela pendiente` sale con 0.
4. En cada capítulo, «Situación» ejecuta `novela cambio <slug> --siguiente`:
   - `01 reaplicar`: `novela aplicar-delta <slug> 1 --reaplicar` copia el capítulo, su delta y su `qa/` desde `v1`, aplica y registra usos. Después `novela checkpoint <slug> 1`.
   - `02 regenerar`: el bucle normal. El `escritor` recibe la capa `cambio` y la versión anterior del capítulo. `validar` comprueba además RF-31. Los revisores revisan contra la base nueva. El `cronista` introduce `hec-103` y vuelve a declarar `hec-102`, y `aplicar-delta` comprueba RF-32.
5. Con `--siguiente = completo`, el operador ejecuta `novela versiones <slug> --novedades` y `novela exportar <slug> --formato md` (o `pdf`, con la 0006), y entrega la versión 2. La versión 1 sigue en `versiones/v1/`.

## 9. Casos límite y gestión de errores

| Caso | Comportamiento esperado | Requisito relacionado |
|------|-------------------------|-----------------------|
| El hecho solo se usa en su capítulo de origen | Se regenera solo ese capítulo | RF-13 |
| El hecho se usa en el último capítulo y en el primero | Se regeneran los dos y se reaplica todo lo intermedio | RF-13, RF-25 |
| Un capítulo posterior menciona el hecho y el `cronista` no lo declaró en `hechos_usados` | No es afectado y se reaplica con su texto antiguo. Si contradice el hecho nuevo, nada mecánico lo detecta. Es un riesgo aceptado (§11), mitigado por RF-35 | RF-02, RF-13 |
| El capítulo regenerado no contiene el hecho nuevo o un requerido | `aplicar-delta` rechaza con `regeneracion:`. El `cronista` se reintenta con la causa (no puede citar lo que no está) y al tercer intento hay `intervencion.md` | RF-32 |
| El capítulo regenerado mata a un personaje que un capítulo reaplicado posterior hace hablar | Si `violaciones` (spec 0002) lo detecta, el `--reaplicar` de ese capítulo sale con 1 y hay intervención. Si no, lo tiene que ver el `continuista` del capítulo regenerado | RF-27, RF-34 |
| El orquestador intenta el bucle normal sobre un capítulo reaplicable | `aplicar-delta` sin `--reaplicar` sale con 2, y `--siguiente` sigue respondiendo `reaplicar` | RF-24, RF-26 |
| El texto nuevo contiene «ignora tus instrucciones…» | Entra en la capa `cambio` como dato delimitado. Los gates de RF-31 y RF-32 no dependen de lo que el modelo haga con él | RF-28, RF-30 |
| El texto nuevo revela la solución del misterio | El guardarraíl del briefing del `escritor` sale con 4. El operador reformula o desiste | RF-30 |
| El hecho cambiado es parte de una pista o de una revelación | Se permite. `validar` exige las mismas pistas e hilos, y el `lector-suspense` y el `continuista` juzgan el fair play. Riesgo en §11 | RF-31 |
| La ficha de plan del capítulo afectado describe el hecho antiguo | El plan no cambia (D21). La capa `cambio` declara que el hecho nuevo sustituye al antiguo, y el `continuista` verifica contra la base nueva | RF-28 |
| Corte a mitad de `novela cambio` | Se repite el comando y se completa o se reinicia según RF-20 | RF-20 |
| Corte entre `--reaplicar` y `checkpoint` | La reanudación repite `--reaplicar`, que es idempotente: copia los mismos bytes y los usos van con `INSERT OR IGNORE` | RF-04, RF-25 |
| Segundo cambio sobre la versión 2 terminada | Crea `versiones/v2/` y la versión 3. `v1` no se toca | RF-17, RF-21 |
| Cambio pedido con otro en curso | Sale con 1 (`cambio en curso: cam-001`) | RF-10 |
| Alguien borra un fichero de `versiones/v1/` a mano | `novela versiones --verificar` sale con 4, y `--reaplicar` sale con 4 si era un fichero que necesita | RF-22, RF-25 |
| Workspace anterior a esta spec | `novela cambio` sale con 4 (`sin tabla usos_de_hecho`). El resto de subcomandos no cambia | RF-05, RF-12 |
| Novela de más de 99 capítulos, con tres dígitos | Rutas por `ws.nn`, y `--siguiente` imprime el número con el ancho del workspace | RF-24 |
| Lock ocupado por el bucle | Sale con 3 sin escribir | RF-09, RF-25 |
| La API sirve la raíz mientras se restablece | Puede ver una novela sin capítulos durante la preparación (< 10 s, RNF-02). La API no ve `versiones/` | RF-19, RF-42 |

## 10. Dependencias y supuestos

- **Spec 0001.** Se reutilizan `WorkspaceRepository` (`escribir`, `bloquear`, `ultimo_checkpoint`, `nn`), `estado_db` (`crear`, `abrir`, `transaccion`, `leer`, `guardar`), `run.abrir`, `huella`, `sha256` y `salida.py`. El modo normal de `aplicar-delta` y su custodia no cambian fuera de una regeneración.
- **Spec 0002** (aceptada, sin implementar). Si se implementa antes, su auditoría de trayectoria y `novela gate` deben admitir la secuencia `--reaplicar` → `checkpoint` sin agentes. Sus invariantes de `validar-delta` se aplican igual en `--reaplicar`, que es lo que da continuidad mecánica a los capítulos reaplicados. Las dos specs tocan `slices/delta/cmd.py` y `novela-continuar.md` (§11).
- **Spec 0006** (Propuesta). RF-40 depende de su `pdf.py`. Si su tabla `apariciones` existe, `--reaplicar` la rellena en la base nueva por el mismo camino de `aplicar-delta`. El ADR de esta spec es el 0004 porque la 0006 reserva el 0003.
- **Spec 0003.** Los cambios de cuerpo de `cronista`, `escritor` y `continuista` no tienen TDD (`AGENTS.md` § Proceso: generar código). Se validan con una novela de humo de 3 capítulos más un cambio, comparando scores (T-15).
- **Sin dependencias nuevas.** La copia usa `shutil` y `sqlite3.Connection.backup` de la stdlib, y el diff usa `difflib`.
- **Supuesto:** `os.replace` de un directorio es atómico en el mismo volumen, en NTFS y en ext4. El workspace entero vive en un volumen (`docs/architecture.md` §4).
- **Supuesto:** `sqlite3.Connection.backup` sobre la base vigente, con el lock tomado y sin escritores, produce una base cuyo `estado_db.leer` es igual al original. CA-16 lo comprueba. No se promete igualdad de bytes del fichero `.db`, solo de contenido, y `version.json` guarda el sha256 del fichero copiado.
- **Supuesto:** con las citas literales de RF-02, el `cronista` declara en `hechos_usados` las menciones de hechos anteriores con la frecuencia suficiente para que la regeneración sea útil. Lo mide la demostración T-15.

## 11. Riesgos

| Riesgo | Probabilidad (A/M/B) | Impacto (A/M/B) | Mitigación |
|--------|----------------------|-----------------|------------|
| El `cronista` (haiku) no declara una mención del hecho en `hechos_usados`, y un capítulo reaplicado contradice el hecho nuevo | A | M | RF-35 y la demostración T-15 miden la cobertura. El riesgo se acepta en `docs/validators.md` §5 con su condición de revisión (D23). El operador puede leer `--simular` antes de gastar cuota |
| El capítulo regenerado cambia más de lo pedido y rompe la continuidad con los reaplicados | M | A | Hechos requeridos (RF-32c), pistas e hilos iguales (RF-31), `violaciones` en cada `--reaplicar` (RF-27), la versión anterior como referencia (RF-29) y el `continuista` |
| El cambio toca una pista o el misterio y rompe el fair play | M | A | Guardarraíl del secreto (RF-30), pistas iguales (RF-31) y `lector-suspense`. El operador revisa `--simular` |
| Regenerar muchos capítulos gasta mucha cuota | M | M | `--simular` imprime el alcance antes. La regeneración usa el bucle desatendido de siempre, que para en checkpoint |
| La reinterpretación de los invariantes 2 y 7 se lee como una puerta para reescribir la historia | M | A | ADR 0004 y una sola vía (`novela cambio`). La versión anterior queda inmutable y verificable (RF-21, RF-22), y la parada por problema retroactivo no cambia |
| Conflictos con la spec 0002 en `delta/cmd.py`, `validar` y el procedimiento | M | M | El modo `--reaplicar` está aislado detrás de su opción. Los gates de regeneración son funciones puras aparte (`de_regeneracion`) |
| El orquestador no consulta `--siguiente` y regenera un capítulo que debía reaplicarse | B | M | RF-26 no deja aplicar sin `--reaplicar` el delta de un reaplicable ni reaplicar un afectado. CA-31 fija el procedimiento |
| El disco crece con cada versión | B | B | RNF-08. No hay borrado de versiones (§3.2), y el riesgo se acepta junto a §5.7 |
| Scores de Langfuse de la versión 1 sustituidos por los de la 2 | M | B | RF-43 con el id versionado |

## 12. Plan de implementación

Cada tarea es un ciclo TDD: test en rojo visto fallar, código mínimo, refactor, y `uv run pytest`, `mypy --strict` y `ruff` en verde antes del commit.

| ID | Tarea | Cubre | Verificación |
|----|-------|-------|--------------|
| T-01 | `docs/adr/0004-versiones-de-la-novela.md`, enmienda del invariante 7 en `AGENTS.md` y `test_adr_de_versiones` | RF-45 | CA-42 en verde |
| T-02 | Tabla `usos_de_hecho` en `esquema.sql`, `UsoDeHecho`, `estado_db.usos`, `capitulos_que_usan`, `registrar_usos` y `asegurar_usos`, con sus tests y la entrada de `docs/definitions.md` | RF-01, RF-05, RF-06, RF-07 | CA-01, CA-06, CA-07 en verde; RNF-01 medido |
| T-03 | `UsoCitado` y `Delta.hechos_usados`, cita e integridad en `violaciones.py`, regeneración de `delta.schema.json` y `docs/definitions.md` en el mismo commit | RF-02 | CA-02 en verde |
| T-04 | `apply.usos` con propiedad e integración en `delta/cmd.py`, con la migración aditiva; `fabrica.CAMBIO`, `hechos_usados` por capítulo y `demo-cambio` | RF-03, RF-04, RF-05 | CA-03, CA-04 (≥ 200 casos), CA-05 en verde; goldens de `DEMO` sin cambios |
| T-05 | `dominio/version.py`, `CambioId` y `slices/cambio/plan.py` (`plan_de_regeneracion`, `id_reservado`, `siguiente_paso`) con propiedades | RF-13, RF-14, RF-15 | CA-13 (≥ 200 casos), CA-14 en verde |
| T-06 | `plataforma/versiones.py`: instantánea, verificación, renombrado, registro, restablecimiento, `estado_db.crear` con `meta` y recuperación tras corte | RF-16, RF-17, RF-18, RF-19, RF-20, RF-21 | CA-15 a CA-19 en verde; RNF-06 y RNF-08 medidos |
| T-07 | `slices/cambio/cmd.py`: petición, `--simular`, `--siguiente`, códigos y línea de log; registro en `cli.py` | RF-08, RF-09, RF-10, RF-11, RF-12, RF-24, RF-33, RF-44 | CA-08 a CA-12, CA-22 en verde; RNF-02 medido |
| T-08 | `aplicar-delta --reaplicar` y el rechazo de un reaplicable sin `--reaplicar` en `delta/cmd.py` | RF-25, RF-26, RF-27, RF-44 | CA-23, CA-24, CA-25 en verde; RNF-03 medido |
| T-09 | Gates de regeneración: `regeneracion_altera_contrato` en `validacion/gates.py` y `violaciones.de_regeneracion`, los dos con propiedad | RF-31, RF-32 | CA-27, CA-28 (≥ 200 casos) en verde |
| T-10 | Capas `cambio` y `version_anterior` en `briefing` y `recipes.yaml`, con el guardarraíl del secreto sobre la capa | RF-28, RF-29, RF-30 | CA-26 en verde; `test_briefing.py` y goldens anteriores sin cambios |
| T-11 | `fabrica.capitulo_regenerado` y `delta_regenerado`, y `tests/test_regeneracion.py` con el recorrido completo y la propiedad de regeneración | RF-13, RF-25, RF-33 | CA-29, CA-30 (≥ 25 casos), CA-41 en verde; RNF-04 y RNF-05 en 0 |
| T-12 | `slices/versiones/`: lista, `--novedades`, `--verificar` y `--diff`, con `novedades.calcular` pura con propiedad | RF-22, RF-36, RF-37, RF-41 | CA-20, CA-33, CA-34 (≥ 200 casos), CA-38 en verde |
| T-13 | Sección de novedades en `export/markdown.py`; página de novedades en `pdf.py` si la spec 0006 está implementada | RF-38, RF-39, RF-40 | CA-35, CA-36 en verde; CA-37 si aplica; RNF-07 en 0 |
| T-14 | Caso de `versiones/` y `cambios/` en `test_hook.py` (y en el hook, si hace falta), e id de score con versión | RF-23, RF-43 | CA-21, CA-40 en verde |
| T-15 | Cuerpos de `cronista.md`, `escritor.md` y `continuista.md`, `novela-continuar.md`, `test_procedimiento_regeneracion` y `test_agentes_nombran_el_cambio`. Demostración con una novela de humo de 3 capítulos más un cambio, en una sesión del harness con datos ficticios | RF-34, RF-35 | CA-31, CA-32 en verde; demostración con `--siguiente = completo`, capítulos reaplicados idénticos y resultado anotado en `docs/validators.md` §4.9 |
| T-16 | Documentación de D23, `test_sin_rutas_de_version` y comprobación de RNF-07 y RNF-09 | RF-42, RF-46 | CA-39, CA-43; RNF-07 y RNF-09 en 0 |

## 13. Estrategia de pruebas

**Datos de prueba.** Todo es ficticio. Personajes, lugares y hechos son los de `backend/tests/fixtures/fabrica.py`, y el texto de la petición es una frase inventada sobre la puerta de la linterna. No hay nombres reales, correos, teléfonos ni identificadores personales.

**Niveles.**

- **Unitario, funciones puras** (sin disco, Hypothesis ≥ 200 casos, obligatorio por tocar `apply.py`, `violaciones.py` y `gates.py`: `docs/validators.md` §3.6):
  - `slices/delta/test_apply.py::test_usos_property` (CA-04).
  - `slices/cambio/test_plan.py::test_plan_de_regeneracion_property` y `::test_id_reservado` (CA-13, CA-14).
  - `slices/delta/test_violaciones.py::test_de_regeneracion_property` (CA-28).
  - `slices/validacion/test_gates.py::test_regeneracion_altera_contrato_property` (CA-27 a nivel de función).
  - `slices/versiones/test_novedades.py::test_novedades_property` (CA-34).
- **Plataforma**:
  - `plataforma/test_esquema.py::test_usos_append_only` (CA-01).
  - `test_estado_db.py::test_capitulos_que_usan` (CA-06, con RNF-01 medido con `time.perf_counter`).
  - `plataforma/test_versiones.py` (CA-16 a CA-19, con los cortes inyectados de CA-18).
- **Integración CLI** con `CliRunner` sobre `NOVELAS_DIR` temporal:
  - `slices/delta/test_delta.py` (CA-02, CA-03, CA-05, CA-23 a CA-25).
  - `slices/cambio/test_cambio.py` (CA-08 a CA-12, CA-15, CA-22).
  - `slices/validacion/test_validacion.py::test_regeneracion` (CA-27).
  - `slices/briefing/test_briefing.py::test_capa_cambio` (CA-26).
  - `slices/versiones/test_versiones.py` (CA-20, CA-33, CA-34, CA-38).
  - `slices/export/test_export.py::test_md_novedades` (CA-35) y los tests existentes sin cambios (CA-36).
  - `slices/checkpoint/test_checkpoint.py::test_id_de_score_versionado` (CA-40).
  - `slices/estado/test_estado.py::test_estado_sin_tabla_usos` (CA-07).
- **Regeneración completa con agente falso**: `tests/test_regeneracion.py::test_recorrido_demo_cambio` (CA-29, CA-41) y `::test_regeneracion_no_toca_reaplicables_property` (CA-30, Hypothesis ≥ 25 casos sin `deadline`). Son los tests de la regeneración selectiva y de «la versión anterior sigue intacta byte a byte».
- **Contrato**:
  - `tests/test_contratos.py`: `test_openapi_al_dia`, `test_state_schema_al_dia`, `test_delta_schema_al_dia`, `test_adr_de_versiones`, `test_procedimiento_regeneracion` y `test_agentes_nombran_el_cambio`.
  - `tests/test_api.py`: `test_sin_rutas_de_version` y CA-07 por la API.
  - `tests/test_hook.py::test_versiones_y_cambios_denegados` (CA-21).
- **Demostración**: T-15. Es la única verificación de los cambios de prompt y de la cobertura real de `hechos_usados`.
- **Opcional**: `slices/export/test_pdf.py::test_pagina_de_novedades` (CA-37), solo con la spec 0006 implementada.
- Ningún test llama a un modelo (RNF-10).

## 14. Matriz de trazabilidad

| RF | Criterios de aceptación | Tareas | Tests |
|----|-------------------------|--------|-------|
| RF-01 | CA-01 | T-02 | `plataforma/test_esquema.py::test_usos_append_only` |
| RF-02 | CA-02 | T-03 | `slices/delta/test_delta.py::test_hechos_usados_cita`, `test_contratos.py::test_delta_schema_al_dia` |
| RF-03 | CA-03, CA-04 | T-04 | `test_delta.py::test_aplicar_registra_usos`, `test_apply.py::test_usos_property` |
| RF-04 | CA-04 | T-04 | `test_apply.py::test_usos_property` |
| RF-05 | CA-05 | T-02, T-04 | `test_delta.py::test_migracion_usos` |
| RF-06 | CA-06 | T-02 | `plataforma/test_estado_db.py::test_capitulos_que_usan` |
| RF-07 | CA-07 | T-02 | `slices/estado/test_estado.py::test_estado_sin_tabla_usos`, `tests/test_api.py::test_estado_sin_tabla_usos` |
| RF-08 | CA-08 | T-07 | `slices/cambio/test_cambio.py::test_simular` |
| RF-09 | CA-09 | T-07 | `test_cambio.py::test_peticion_registrada` |
| RF-10 | CA-10 | T-07 | `test_cambio.py::test_precondiciones` |
| RF-11 | CA-11 | T-07 | `test_cambio.py::test_argumentos_invalidos` |
| RF-12 | CA-12 | T-07 | `test_cambio.py::test_workspace_sin_tabla_o_sin_ids` |
| RF-13 | CA-13, CA-30 | T-05, T-11 | `slices/cambio/test_plan.py::test_plan_de_regeneracion_property`, `tests/test_regeneracion.py::test_regeneracion_no_toca_reaplicables_property` |
| RF-14 | CA-13 | T-05 | `test_plan.py::test_plan_de_regeneracion_property` |
| RF-15 | CA-14 | T-05 | `test_plan.py::test_id_reservado` |
| RF-16 | CA-15 | T-06 | `test_cambio.py::test_numero_de_version` |
| RF-17 | CA-16 | T-06 | `plataforma/test_versiones.py::test_instantanea_byte_a_byte` |
| RF-18 | CA-16 | T-06 | `test_versiones.py::test_instantanea_excluye` |
| RF-19 | CA-17 | T-06 | `test_versiones.py::test_raiz_restablecida` |
| RF-20 | CA-18 | T-06 | `test_versiones.py::test_recuperacion_tras_corte` |
| RF-21 | CA-19 | T-06 | `test_versiones.py::test_version_inmutable`, `tests/test_regeneracion.py::test_recorrido_demo_cambio` |
| RF-22 | CA-20 | T-12 | `slices/versiones/test_versiones.py::test_verificar` |
| RF-23 | CA-21 | T-14 | `tests/test_hook.py::test_versiones_y_cambios_denegados` |
| RF-24 | CA-22 | T-07 | `test_cambio.py::test_siguiente` |
| RF-25 | CA-23, CA-30 | T-08, T-11 | `test_delta.py::test_reaplicar`, `test_regeneracion.py::test_regeneracion_no_toca_reaplicables_property` |
| RF-26 | CA-24 | T-08 | `test_delta.py::test_reaplicar_fuera_de_modo` |
| RF-27 | CA-25 | T-08 | `test_delta.py::test_reaplicar_rechazado` |
| RF-28 | CA-26 | T-10 | `slices/briefing/test_briefing.py::test_capa_cambio` |
| RF-29 | CA-26 | T-10 | `test_briefing.py::test_capa_cambio` |
| RF-30 | CA-26 | T-10 | `test_briefing.py::test_capa_cambio_sin_secreto` |
| RF-31 | CA-27 | T-09 | `slices/validacion/test_gates.py::test_regeneracion_altera_contrato_property`, `test_validacion.py::test_regeneracion` |
| RF-32 | CA-28 | T-09 | `slices/delta/test_violaciones.py::test_de_regeneracion_property`, `test_delta.py::test_regeneracion_rechazada` |
| RF-33 | CA-29 | T-07, T-11 | `tests/test_regeneracion.py::test_recorrido_demo_cambio` |
| RF-34 | CA-31 | T-15 | `test_contratos.py::test_procedimiento_regeneracion`; demostración T-15 |
| RF-35 | CA-32 | T-15 | `test_contratos.py::test_agentes_nombran_el_cambio`; demostración T-15 |
| RF-36 | CA-33 | T-12 | `slices/versiones/test_versiones.py::test_listado` |
| RF-37 | CA-34 | T-12 | `slices/versiones/test_novedades.py::test_novedades_property`, `test_versiones.py::test_novedades_cli` |
| RF-38 | CA-35 | T-13 | `slices/export/test_export.py::test_md_novedades` |
| RF-39 | CA-36 | T-13 | `test_export.py::test_md_concatena_en_orden`, `::test_epub_reabrible` |
| RF-40 | CA-37 | T-13 | `slices/export/test_pdf.py::test_pagina_de_novedades` (con la spec 0006) |
| RF-41 | CA-38 | T-12 | `test_versiones.py::test_diff` |
| RF-42 | CA-39 | T-16 | `test_contratos.py::test_openapi_al_dia`, `::test_state_schema_al_dia`, `test_api.py::test_sin_rutas_de_version` |
| RF-43 | CA-40 | T-14 | `slices/checkpoint/test_checkpoint.py::test_id_de_score_versionado` |
| RF-44 | CA-41 | T-07, T-08, T-11 | `tests/test_regeneracion.py::test_recorrido_demo_cambio` |
| RF-45 | CA-42 | T-01 | `test_contratos.py::test_adr_de_versiones` |
| RF-46 | CA-43 | T-16 | Inspección del commit de cierre (§13, nivel de contrato y documentación) |

## 16. Decisiones

Ver decisions.md

- D1 — Modelo de versión: base nueva por versión y la anterior intacta
- D2 — Convivencia con los invariantes 2 y 7: ADR 0004 y enmienda del invariante 7
- D3 — Origen de los usos hecho→capítulo
- D4 — Campo `hechos_usados` en el delta
- D5 — Workspaces anteriores a esta spec
- D6 — Cuándo se admite una petición de cambio
- D7 — Dónde se registran la petición y el índice de versiones
- D8 — Qué entra en la instantánea de una versión
- D9 — Secuencia de preparación y recuperación ante corte
- D10 — Creación de la base vacía de la versión nueva
- D11 — Reaplicación de los capítulos no afectados
- D12 — Quién decide el siguiente paso de la regeneración
- D13 — Conjunto de capítulos afectados, sin cascada
- D14 — Gates de continuidad de la regeneración
- D15 — Id del hecho nuevo
- D16 — Contexto del escritor en la regeneración
- D17 — La petición como dato no confiable
- D18 — Novedades, marca y diff entre versiones
- D19 — La API y el frontend no cambian
- D20 — Scores de Langfuse por versión
- D21 — El canon y el plan no cambian
- D22 — Identificadores `cam-` y `vN`
- D23 — Documentación que se actualiza
- D24 — Estrategia de pruebas
